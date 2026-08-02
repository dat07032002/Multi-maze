import concurrent.futures
import json
from collections import defaultdict, deque
from functools import partial as bind
from pathlib import Path

import embodied

from . import chunk as chunklib


class Saver:
    # Smallest partial chunk a periodic save will write out. Rotating a buffer
    # holding a handful of steps is correct but fragments the replay: a run
    # that checkpoints often, with one buffer per parallel worker, accumulates
    # many tiny files that every later Chunk.scan and load has to walk. An
    # explicit save(wait=True), which is what the end of training and any
    # deliberate flush use, still writes every buffer regardless of length, so
    # only an unclean crash can lose the sub-threshold tail.
    MIN_PERIODIC_CHUNK = 128

    def __init__(self, directory, chunks=1024):
        self.directory = embodied.Path(directory)
        self.directory.mkdirs()
        self.chunks = chunks
        self.buffers = defaultdict(bind(chunklib.Chunk, chunks))
        self.workers = concurrent.futures.ThreadPoolExecutor(16)
        self.promises = deque()
        self.loading = False
        self.load_report = {
            "selected_chunks": 0,
            "accepted_chunks": 0,
            "rejected_chunks": 0,
            "rejections": [],
        }

    def add(self, step, worker):
        if self.loading:
            return
        buffer = self.buffers[worker]
        buffer.append(step)
        if buffer.length >= self.chunks:
            print("Saving chunk")
            self.buffers[worker] = buffer.successor = chunklib.Chunk(self.chunks)
            self.promises.append(self.workers.submit(buffer.save, self.directory))
            for promise in [x for x in self.promises if x.done()]:
                promise.result()
                self.promises.remove(promise)

    def save(self, wait=False):
        threshold = 1 if wait else self.MIN_PERIODIC_CHUNK
        for worker, buffer in tuple(self.buffers.items()):
            if buffer.length >= threshold:
                # Rotate partial chunks exactly once. Keeping the same buffer
                # here caused every checkpoint to resubmit it and could leave
                # duplicate writes pending during process shutdown.
                self.buffers[worker] = buffer.successor = chunklib.Chunk(self.chunks)
                self.promises.append(self.workers.submit(buffer.save, self.directory))
        if wait:
            [x.result() for x in self.promises]
            self.promises.clear()

    def close(self):
        if self.workers is None:
            return
        [promise.result() for promise in self.promises]
        self.promises.clear()
        self.workers.shutdown(wait=True, cancel_futures=False)
        self.workers = None

    def load(self, capacity, length):
        filenames = chunklib.Chunk.scan(self.directory, capacity, length - 1)
        if not filenames:
            return
        threads = min(len(filenames), 32)
        with concurrent.futures.ThreadPoolExecutor(threads) as executor:
            futures = [executor.submit(chunklib.Chunk.load, name) for name in filenames]
            chunks = []
            rejections = []
            for filename, future in zip(filenames, futures):
                try:
                    chunk = future.result()
                    failures = embodied.nonfinite_fields(chunk.data)
                    if failures:
                        raise embodied.NonFiniteDataError(str(failures))
                except Exception as error:
                    rejections.append(
                        {"filename": str(filename), "reason": str(error)}
                    )
                    print(f"Skipping invalid replay chunk {filename}: {error}")
                else:
                    chunks.append(chunk)
        self.load_report = {
            "selected_chunks": len(filenames),
            "accepted_chunks": len(chunks),
            "rejected_chunks": len(rejections),
            "rejections": rejections,
        }
        print(
            "Replay load validation: "
            f"accepted {len(chunks)}/{len(filenames)} chunks; "
            f"rejected {len(rejections)}."
        )
        report_path = Path(str(self.directory)) / "replay_load_report.json"
        temporary = report_path.with_suffix(report_path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(self.load_report, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        temporary.replace(report_path)
        if not chunks:
            return
        streamids = {}
        for chunk in reversed(sorted(chunks, key=lambda x: x.time)):
            if chunk.successor not in streamids:
                streamids[chunk.uuid] = int(embodied.uuid())
            else:
                streamids[chunk.uuid] = streamids[chunk.successor]
        self.loading = True
        for i, chunk in enumerate(chunks):
            stream = streamids[chunk.uuid]
            for index in range(chunk.length):
                step = {k: v[index] for k, v in chunk.data.items()}
                yield step, stream
            # Free memory early to not require twice the replay capacity.
            chunks[i] = None
            del chunk
        self.loading = False
