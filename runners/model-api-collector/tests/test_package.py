def test_package_exposes_version():
    import model_api_collector

    assert model_api_collector.__version__ == "0.1.0"
