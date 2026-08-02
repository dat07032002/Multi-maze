import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np


DREAMER_PACKAGE = Path(__file__).resolve().parents[2] / "dreamerv3" / "dreamerv3"
sys.path.insert(0, str(DREAMER_PACKAGE))

from embodied.core.checkpoint import Checkpoint  # noqa: E402
from embodied.core.logger import AsyncOutput, TensorBoardOutput  # noqa: E402
from embodied.replay.saver import Saver  # noqa: E402


class AsyncResourceCleanupTests(unittest.TestCase):
    def test_checkpoint_close_drains_and_stops_worker(self):
        checkpoint = Checkpoint(parallel=True)
        checkpoint.close()
        self.assertIsNone(checkpoint._worker)
        checkpoint.close()

    def test_async_output_close_drains_and_stops_worker(self):
        values = []
        output = AsyncOutput(values.extend, parallel=True)
        output((1, 2, 3))
        output.close()
        self.assertEqual(values, [1, 2, 3])
        self.assertIsNone(output._executor)
        output.close()

    def test_replay_saver_close_stops_workers(self):
        with tempfile.TemporaryDirectory() as directory:
            saver = Saver(directory)
            saver.close()
            self.assertIsNone(saver.workers)
            saver.close()

    def test_replay_partial_chunk_is_not_resubmitted(self):
        with tempfile.TemporaryDirectory() as directory:
            saver = Saver(directory)
            saver.add({"reward": np.asarray(1.0, np.float32)}, worker=0)
            saver.save(wait=True)
            first = sorted(Path(directory).glob("*.npz"))
            saver.save(wait=True)
            second = sorted(Path(directory).glob("*.npz"))
            saver.close()
            self.assertEqual(len(first), 1)
            self.assertEqual(second, first)

    def test_local_tensorboard_output_closes_without_a_size_checker(self):
        """The size checker only exists for gs:// logdirs.

        close() inspects the checker and its pending promise unconditionally,
        so any local-logdir run raised AttributeError on shutdown. The tagmaze
        profiles set tensorboard: False, so this never fired on the server, but
        the default in configs.yaml is True and the trap was one config flag
        away.
        """
        with tempfile.TemporaryDirectory() as directory:
            output = TensorBoardOutput(directory, parallel=False)
            self.assertFalse(output._maxsize)
            output.close()
            output.close()

    def test_periodic_save_does_not_fragment_replay_into_tiny_chunks(self):
        """A short buffer must wait rather than become its own file.

        One file per worker per checkpoint is correct but makes every later
        Chunk.scan walk a long tail of near-empty chunks.
        """
        with tempfile.TemporaryDirectory() as directory:
            saver = Saver(directory)
            for _ in range(Saver.MIN_PERIODIC_CHUNK - 1):
                saver.add({"reward": np.asarray(1.0, np.float32)}, worker=0)
            saver.save(wait=False)
            self.assertEqual(sorted(Path(directory).glob("*.npz")), [])
            saver.add({"reward": np.asarray(1.0, np.float32)}, worker=0)
            saver.save(wait=False)
            [promise.result() for promise in saver.promises]
            self.assertEqual(len(sorted(Path(directory).glob("*.npz"))), 1)
            saver.close()

    def test_explicit_flush_still_writes_every_partial_chunk(self):
        """The end-of-training flush must not lose the sub-threshold tail."""
        with tempfile.TemporaryDirectory() as directory:
            saver = Saver(directory)
            saver.add({"reward": np.asarray(1.0, np.float32)}, worker=0)
            saver.add({"reward": np.asarray(2.0, np.float32)}, worker=1)
            saver.save(wait=True)
            self.assertEqual(len(sorted(Path(directory).glob("*.npz"))), 2)
            saver.close()


if __name__ == "__main__":
    unittest.main()
