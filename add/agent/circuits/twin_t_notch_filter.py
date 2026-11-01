"""Generate a Falstad (CircuitJS) passive twin-T notch filter netlist."""

from . import _active_filters as af


def twin_t_notch_filter(notch_frequency: float) -> str:
    """Generate a Falstad-format passive twin-T notch (band-stop) filter.

    Two T networks in parallel between the input and the output: a low-pass T of R - R with
    2C to ground, and a high-pass T of C - C with R/2 to ground. At f0 = 1 / (2 pi R C) the
    two paths cancel and the output is (ideally) zero, while low and high frequencies pass
    with a gain of 1. The 2C and R/2 elements are built from two equal parts in parallel, so
    the ratios are exact and the notch is as deep as the parts allow.

    C is a decade value chosen so R lands in 1-100 kOhm, and R is the nearest standard (E24)
    value, so the notch frequency differs slightly from the request. A FilterAccuracyWarning
    reports the rounding. The filter is passive and unbuffered: a load on its output moves
    and fills the notch, so follow it with a buffer when it drives anything.

    Args:
        notch_frequency: Desired frequency of the notch in Hz.

    Returns:
        The Falstad circuit text, ready to load into circuitjs1.

    Raises:
        ValueError: If notch_frequency is not a finite number > 0 or is out of range.

    Warns:
        FilterAccuracyWarning: If standard values change the notch frequency.
    """
    R, C, f_act = af.pick_rc(notch_frequency, "notch frequency")
    el = [af.sweep_source(f_act),
          # low-pass T: R - R, 2C (two C in parallel) to ground
          af.res(240, 160, 320, 160, R),
          af.res(320, 160, 416, 160, R),
          "w 320 160 320 192 0",
          "w 320 192 352 192 0",
          af.cap(320, 192, 320, 256, C),
          af.cap(352, 192, 352, 256, C),
          "w 320 256 336 256 0",
          "w 336 256 352 256 0",
          "g 336 256 336 288 0",
          # high-pass T: C - C, R/2 (two R in parallel) to ground
          "w 240 160 240 384 0",
          af.cap(240, 384, 320, 384, C),
          af.cap(320, 384, 416, 384, C),
          "w 320 384 320 416 0",
          "w 320 416 352 416 0",
          af.res(320, 416, 320, 480, R),
          af.res(352, 416, 352, 480, R),
          "w 320 480 336 480 0",
          "w 336 480 352 480 0",
          "g 336 480 336 512 0",
          # both Ts meet at the output
          "w 416 384 416 160 0",
          "O 416 160 480 160 0"]
    return af.assemble(el, f_act, af.SWEEP_VOLTAGE)
