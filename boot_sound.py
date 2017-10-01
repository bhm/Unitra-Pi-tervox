from playable_file import PlayableFile


class BootSound(PlayableFile):
    DEFAULT_BOOT_FILE = "boot-up.wav"

    def __init__(self, boot_sound=DEFAULT_BOOT_FILE):
        super().__init__(boot_sound, silent_fail=True)
