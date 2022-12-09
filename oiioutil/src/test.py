import os
import timeit
import sys



os.add_dll_directory('C:/dev/install/bin')
sys.path.append('C:/dev/install/bin')


def func1():
    import bookmarks_oiio
    bookmarks_oiio.make_thumbnail('C:/temp/source.png', 'C:/temp/out.png', 512)

def oiio_make_thumbnail(source, destination, size):
    import OpenImageIO
    accepted_codecs = ('h.264', 'h264', 'mpeg-4', 'mpeg4')

    def _get_scaled_spec(source_spec, size):
        w = source_spec.width
        h = source_spec.height
        factor = float(size) / max(float(w), float(h))
        w *= factor
        h *= factor

        s = OpenImageIO.ImageSpec(int(w), int(h), 4, OpenImageIO.UINT8)
        s.channelnames = ('R', 'G', 'B', 'A')
        s.alpha_channel = 3
        s.attribute('oiio:ColorSpace', 'sRGB')
        s.attribute('oiio:Gamma', '0.454545')
        return s

    def _shuffle_channels(buf, source_spec):
        if int(source_spec.nchannels) < 3:
            buf = OpenImageIO.ImageBufAlgo.channels(
                buf,
                (source_spec.channelnames[0], source_spec.channelnames[0],
                    source_spec.channelnames[0]),
                ('R', 'G', 'B')
            )
        elif int(source_spec.nchannels) > 4:
            if source_spec.channelindex('A') > -1:
                buf = OpenImageIO.ImageBufAlgo.channels(
                    buf, ('R', 'G', 'B', 'A'), ('R', 'G', 'B', 'A'))
            else:
                buf = OpenImageIO.ImageBufAlgo.channels(
                    buf, ('R', 'G', 'B'), ('R', 'G', 'B'))
        return buf

    def _resize(buf, destination_spec):
        return OpenImageIO.ImageBufAlgo.resample(
            buf, roi=destination_spec.roi, interpolate=True)

    def _flatten(buf, source_spec):
        if source_spec.get_int_attribute('deep', defaultval=-1) != 1:
            return buf
        if source_spec.deep:
            buf = OpenImageIO.ImageBufAlgo.flatten(buf)
        return buf

    def _colorconvert(buf, source_spec):
        if source_spec.get_int_attribute('oiio:Movie') == 1:
            return buf
        colorspace = source_spec.get_string_attribute('oiio:ColorSpace')
        try:
            if colorspace == 'linear':
                buf = OpenImageIO.ImageBufAlgo._colorconvert(
                    buf, colorspace, 'sRGB')
        except:
            pass
        return buf

    def _checker(buf, source_spec, destination_spec):
        if source_spec.get_int_attribute('oiio:Movie', defaultval=-1) == 1:
            return buf
        if buf.nchannels <= 3:
            return buf
        background_buf = OpenImageIO.ImageBuf(destination_spec)
        OpenImageIO.ImageBufAlgo._checker(
            background_buf,
            12, 12, 1,
            (0.3, 0.3, 0.3),
            (0.2, 0.2, 0.2)
        )
        buf = OpenImageIO.ImageBufAlgo.over(buf, background_buf)
        return buf


    def oiio_get_buf(source, subimage=0):
        import OpenImageIO
        if '.' not in source:
            return None
        ext = source.split('.')[-1].lower()
        if not OpenImageIO.is_imageio_format_name(ext):
            return None

        i = OpenImageIO.ImageInput.create(ext)
        if not i or not i.valid_file(source):
            i.close()
            return None

        config = OpenImageIO.ImageSpec()
        config.format = OpenImageIO.TypeDesc(OpenImageIO.FLOAT)

        buf = OpenImageIO.ImageBuf()
        buf.reset(source, subimage, 0, config=config)
        if buf.has_error:
            return None
        return buf

    if not os.path.isfile(source):
        return
    _lock_path = f'{destination}.lock'
    if os.path.isfile(_lock_path):
        return

    with open(_lock_path, 'a', encoding='utf8') as _f:
        pass

    buf = oiio_get_buf(source)
    if not buf:
        os.remove(_lock_path)
        return False

    source_spec = buf.spec()

    source_spec['ICCProfile'] = 0
    source_spec.erase_attribute('ICCProfile')

    if source_spec.get_int_attribute('oiio:Movie', -1) == 1:
        # Load the middle frame of the video
        buf = oiio_get_buf(source, subimage=int(buf.nsubimages / 2))

        is_gif = source_spec.get_int_attribute('gif:LoopCount', -1) >= 0

        # I'm having issues working with very short movie files that contain only a couple of frames,
        # so, let's ignore those ( except gifs, those are fine)
        if not is_gif and source_spec.get_int_attribute('oiio:subimages', -1) <= 2:
            os.remove(_lock_path)
            return False

        # [BUG] Not all codec formats are supported by ffmpeg. There does
        # not seem to be (?) error handling and an unsupported codec will
        # crash ffmpeg and the rest of the app.
        codec_name = source_spec.get_string_attribute('ffmpeg:codec_name')
        if not is_gif and codec_name:
            if not [f for f in accepted_codecs if f.lower() in codec_name.lower()]:
                os.remove(_lock_path)
                return False

    destination_spec = _get_scaled_spec(source_spec, size)
    if size != -1:
        buf = _resize(buf, destination_spec)
    buf = _shuffle_channels(buf, source_spec)
    buf = _flatten(buf, source_spec)
    buf = _colorconvert(buf, source_spec)

    spec = buf.spec()
    buf.set_write_format(OpenImageIO.UINT8)

    # On some dpx images I'm getting "GammaCorrectedinf"
    if 'gammacorrectedinf' in spec.get_string_attribute('oiio:ColorSpace').lower():
        spec['oiio:ColorSpace'] = 'sRGB'
        spec['oiio:Gamma'] = '0.454545'

    # Create a lock file before writing
    success = buf.write(destination, dtype=OpenImageIO.UINT8)
    os.remove(_lock_path)

    if not success:
        os.remove(destination)

        return False

    return True

def func2():
    oiio_make_thumbnail('C:/temp/source.png', 'C:/temp/out.png', 512)

if __name__ == '__main__':
    n = 500
    print(timeit.timeit(func2, number=n))
    print(timeit.timeit(func1, number=n))