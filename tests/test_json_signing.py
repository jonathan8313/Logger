import json
from jvlogger import JVLogger
from jvlogger.signing import HMACSigner

def test_json_log_is_signed(temp_log_dir):
    key = HMACSigner.generate_key()
    signer = HMACSigner(key)

    wrapper = JVLogger(
        name="signed_app",
        signer=signer,
        install_excepthooks=False,
        log_dir=temp_log_dir,
    )
    logger = wrapper.get_logger()
    logger.info("signed message")
    wrapper.close()

    log_path = temp_log_dir / "signed_app.json"
    assert log_path.exists()

    line = log_path.read_text(encoding="utf-8").strip()
    entry = json.loads(line)

    assert "signature" in entry

    signature = entry.pop("signature")
    canonical = json.dumps(entry, sort_keys=True, separators=(",", ":")).encode("utf-8")

    assert signer.verify(canonical, signature) is True
