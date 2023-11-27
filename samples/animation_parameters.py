from cntxt import Context


DEFAULT_DURATION = 0.3  # seconds
EASE_IN_OUT = "ease_in_out"
EASE_OUT_IN = "ease_out_in"


# Animation settings

class Animation(Context):
    duration: float = DEFAULT_DURATION
    ease: str = None
    start_delay: float = None
    end_delay: float = None


# Convenience context managers

def duration(duration=DEFAULT_DURATION):
    return Animation.set(duration=duration)


def ease(ease_func=EASE_IN_OUT):
    return Animation.set(ease=ease_func)


def start_delay(start_delay=0.3):
    return Animation.set(start_delay=start_delay)


def end_delay(end_delay=0.3):
    return Animation.set(end_delay=end_delay)
