from bot.services.transcription import transcribe_audio


def test_missing_file_returns_clear_message(tmp_path):
    missing = tmp_path / "does_not_exist.ogg"

    result = transcribe_audio(str(missing))

    assert result == "[Error: Audio file not found]"


def test_empty_file_returns_error(tmp_path):
    empty = tmp_path / "blank.wav"
    empty.write_bytes(b"")

    result = transcribe_audio(str(empty))

    assert result == "[Error: Audio file is empty]"
