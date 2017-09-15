from os import path
import sounddevice as sd
import soundfile as sf


class PlayableFile(object):
    def __init__(self, file_path):
        if file_path is None:
            raise AttributeError('missing a file to play')

        if path.exists(file_path):
            self._filepath = file_path
        else:
            # try get a local file
            self._filename = file_path
            self._filepath = path.dirname(__file__) + "/" + self._filename

        if not path.exists(self._filepath):
            raise AttributeError(self._filepath + ' does not exist')
        else:
            print("Playing %s" % self._filepath)

    def play(self):
        data, fs = sf.read(file=self._filepath, dtype='float32')
        sd.play(data, samplerate=44100)
        status = sd.wait()
        if status:
            print("error %s" % status)
