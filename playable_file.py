from os import path
import sounddevice as sd
import soundfile as sf


class PlayableFile(object):
    def __init__(self, file_path, silent_fail=False):
        self.silent_fail = silent_fail
        if file_path is None:
            raise AttributeError('missing a file to play')

        if path.exists(file_path):
            self._filepath = file_path
        else:
            # try get a local file
            self._filename = file_path
            self._filepath = path.dirname(__file__) + "/" + self._filename

        self.__check_for_file()

    def exists(self):
        return path.exists(self._filepath)

    def play(self):
        self.__check_for_file()
        print("Playing %s" % self._filepath)
        data, fs = sf.read(file=self._filepath, dtype='float32')
        sd.play(data, samplerate=44100)
        status = sd.wait()
        if status:
            print("error %s" % status)

    def __check_for_file(self):
        if not self.exists() and not self.silent_fail:
            raise AttributeError(self._filepath + ' does not exist')
