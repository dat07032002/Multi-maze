import numpy as np
import pytest

from tag_state_estimation.core.bno086_protocol import parse_bno086_line


def test_parses_tag_csv_and_normalizes_quaternion():
    sample = parse_bno086_line("TAG_IMU,0,0,0,2,0.1,0.2,0.3,1,2,3,3")
    assert np.allclose(sample.quaternion_xyzw, [0, 0, 0, 1])
    assert sample.accuracy == 3


def test_parses_named_json_without_field_order_ambiguity():
    sample = parse_bno086_line(
        '{"qw":1,"qz":0,"qy":0,"qx":0,"gx":0,"gy":0,"gz":0,'
        '"ax":0,"ay":0,"az":9.81,"accuracy":2}'
    )
    assert np.allclose(sample.linear_acceleration_xyz, [0, 0, 9.81])


def test_rejects_unlabelled_csv():
    with pytest.raises(ValueError):
        parse_bno086_line("0,0,0,1,0,0,0,0,0,9.81,3")
