"""Light and sound show using SpikeBuilder.

Demonstrates:
- All LightImage enum values
- b.light.show_image(), show_image_for(), set_pixel(), clear()
- b.light.set_center_button() with Color enum
- b.sound.beep_for(), play(), stop()
- b.flow.repeat() loop with indexed image slideshow
- b.wait.ms() for timing

Compile::

    outputllsp3 build examples/04_spike_builder_display.py --out display.llsp3
"""
from outputllsp3 import LightImage, Color

def build(project, api, ns=None):
    from outputllsp3 import SpikeBuilder
    b = SpikeBuilder(project)

    b.flow.start(
        # Rapid image slideshow
        b.light.show_image_for(LightImage.HEART, 0.5),
        b.light.show_image_for(LightImage.HAPPY, 0.5),
        b.light.show_image_for(LightImage.SURPRISED, 0.5),
        b.light.show_image_for(LightImage.SILLY, 0.5),
        b.light.show_image_for(LightImage.SKULL, 0.5),

        # Custom pixel art (smiley)
        b.light.clear(),
        b.light.set_pixel(1, 1, 100),   # left eye
        b.light.set_pixel(3, 1, 100),   # right eye
        b.light.set_pixel(0, 3, 100),   # smile left
        b.light.set_pixel(1, 4, 100),   # smile mid-left
        b.light.set_pixel(2, 4, 100),   # smile centre
        b.light.set_pixel(3, 4, 100),   # smile mid-right
        b.light.set_pixel(4, 3, 100),   # smile right
        b.wait.seconds(1),

        # Hub button colour cycle
        b.light.set_center_button(Color.RED),
        b.sound.beep_for(60, 0.2),
        b.light.set_center_button(Color.GREEN),
        b.sound.beep_for(64, 0.2),
        b.light.set_center_button(Color.BLUE),
        b.sound.beep_for(67, 0.2),
        b.light.set_center_button(Color.WHITE),

        # Final fanfare
        b.light.show_image(LightImage.YES),
        b.sound.beep_for(72, 0.5),
        b.sound.beep_for(76, 0.5),
        b.sound.beep_for(79, 1.0),
        b.light.clear(),
    )
