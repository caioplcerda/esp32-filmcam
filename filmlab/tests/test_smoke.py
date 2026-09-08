import filmlab


def test_package_exposes_version():
    assert isinstance(filmlab.__version__, str)
    assert filmlab.__version__
