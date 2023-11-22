from samples.animation_parameters import Animation
from samples.animation_parameters import EASE_OUT_IN
from samples.animation_parameters import duration
from samples.animation_parameters import ease
from samples.plugins.configured import core_function

def test_plugins():
    assert core_function() == ["main", "plugin"]


def test_animation():
    with ease(EASE_OUT_IN):
        assert Animation.duration == 0.3
        assert Animation.ease == EASE_OUT_IN

        # Introduce some graphical elements here, use Animation to provide animation properties

        with duration(1.0):
            assert Animation.duration == 1.0
            assert Animation.ease == EASE_OUT_IN

            # Introduce other elements here, with a slower movement but consistent ease function
