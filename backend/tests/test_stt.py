"""Dịch vụ STT (ADR-006, giai đoạn 1). SQLite + engine giả + (phần lớn) ffmpeg giả.

Không cần Postgres, GPU hay model.

Chỉ nhóm "ffmpeg thật" ở cuối cần ffmpeg và tự bỏ qua nếu máy không có.
"""

import math
import struct
import wave
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.api.deps import UserInfo, get_db, get_stt_user
from app.config import settings
from app.main import create_app
from app.models import SttJob
from app.stt import audio, files, jobs, service
from app.stt.engines import ENGINES, get_engine, list_engines
from app.stt.engines.base import Segment
from app.stt.engines.fake import FakeEngine
from app.stt.errors import AudioTooLong, UnknownEngine, UnsupportedAudio

A = UserInfo(1, "binh.le", "staff", "Kinh doanh", "Lê Văn Bình")
B = UserInfo(2, "ha.pham", "staff", "Nhân sự", "Phạm Hà")
ADMIN = UserInfo(9, "quan.tri", "admin", "CNTT", "Quản trị")

FAKE_SECONDS = 12.0
HAVE_FFMPEG = audio.find_ffmpeg() is not None


def fake_probe(src_path, *, max_seconds):
    """Thay ffmpeg lúc nhận job: nội dung bắt đầu bằng BAD! = không phải âm thanh, LONG = khai báo quá dài."""
    head = Path(src_path).read_bytes()[:4]
    if head == b"BAD!":
        raise UnsupportedAudio("Không đọc được file này như âm thanh hoặc video có tiếng")
    if head == b"LONG":
        raise AudioTooLong("Ghi âm dài hơn giới hạn")
    return FAKE_SECONDS


def fake_convert(src_path, dst_path, *, max_seconds):
    """Thay ffmpeg lúc xử lý: BAD2 = đổi định dạng hỏng giữa chừng, LON2 = thời lượng thật quá dài."""
    head = Path(src_path).read_bytes()[:4]
    if head == b"BAD2":
        raise UnsupportedAudio("Không đọc được file này như âm thanh hoặc video có tiếng")
    if head == b"LON2":
        raise AudioTooLong("Ghi âm dài hơn giới hạn")
    Path(dst_path).write_bytes(b"wav")
    return FAKE_SECONDS


class HookEngine(FakeEngine):
    """Engine giả cho phép chèn hành vi (xóa job, ném lỗi) trước mỗi đoạn."""

    def __init__(self):
        super().__init__()
        self.hook = None
        self.closed = False

    def transcribe(self, audio_path, *, language):
        self.calls += 1
        self.languages.append(language)
        self.paths.append(audio_path)
        try:
            for seg in self.segments:
                if self.hook:
                    self.hook()
                yield seg
        finally:
            self.closed = True


@pytest.fixture
def env(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'jobs.db'}", connect_args={"check_same_thread": False})
    SttJob.__table__.create(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    audit, usage = [], []
    eng = HookEngine()
    tmp = tmp_path / "stt-tmp"

    monkeypatch.setattr(settings, "stt_tmp_dir", str(tmp))
    monkeypatch.setattr(settings, "stt_engine", "fake")
    monkeypatch.delitem(ENGINES, "whisper", raising=False)  # engine thật không được lẫn vào test dùng engine giả
    monkeypatch.setattr(jobs, "session_factory", factory)
    monkeypatch.setattr(jobs, "PROGRESS_EVERY_S", 0)
    monkeypatch.setattr(jobs, "_audit", lambda db, uid, event, detail: audit.append((uid, event, detail)))
    monkeypatch.setattr(jobs, "_usage", lambda db, user, engine_name: usage.append((user.id, engine_name)))
    monkeypatch.setattr(jobs, "_submit", lambda fn, *args: fn(*args))  # chạy đồng bộ cho dễ kiểm tra
    monkeypatch.setattr(audio, "probe", fake_probe)
    monkeypatch.setattr(audio, "convert", fake_convert)
    monkeypatch.setattr(audio, "require_ffmpeg", lambda: "ffmpeg")
    monkeypatch.setitem(ENGINES, "fake", lambda: eng)

    app = create_app()

    def db_override():
        s = factory()
        try:
            yield s
        finally:
            s.close()

    who = {"user": A}
    app.dependency_overrides[get_db] = db_override
    app.dependency_overrides[get_stt_user] = lambda: who["user"]
    return SimpleNamespace(
        client=TestClient(app), factory=factory, audit=audit, usage=usage, eng=eng, who=who, tmp=tmp,
        monkeypatch=monkeypatch,
    )


def post(env, data: bytes = b"AUDIO-GIA", name="hop.mp3", mime="audio/mpeg", **params):
    return env.client.post("/api/stt/jobs", params=params, files={"file": (name, data, mime)})


def rows(env) -> list:
    with env.factory() as db:
        return list(db.scalars(select(SttJob)))


def leftovers(env) -> list[str]:
    """Tệp còn sót trong thư mục tạm; sau mỗi job phải rỗng."""
    return [p.name for p in env.tmp.iterdir()] if env.tmp.exists() else []


# ---------- đường đi chính ----------

def test_tao_job_tra_202_va_chay_xong(env):
    r = post(env)
    assert r.status_code == 202
    body = r.json()
    assert r.headers["location"] == f"/api/stt/jobs/{body['job_id']}"
    assert body["status"] == "queued" and body["engine"] == "fake" and body["language"] == "vi"

    got = env.client.get(f"/api/stt/jobs/{body['job_id']}").json()
    assert got["status"] == "done" and got["finished_at"] is not None
    assert got["duration_s"] == got["done_s"] == FAKE_SECONDS
    assert [s["text"] for s in got["segments"]] == [
        "Xin chào mọi người.", "Hôm nay ta bàn về tiến độ dự án.", "Cảm ơn.",
    ]
    assert got["segments"][1] == {"start": 4.0, "end": 9.5, "text": "Hôm nay ta bàn về tiến độ dự án.", "speaker": None}
    assert leftovers(env) == []  # đã xóa cả file gốc lẫn WAV


def test_ngon_ngu_mac_dinh_va_chon_rieng(env):
    post(env)
    post(env, language="en")
    assert env.eng.languages == ["vi", "en"]


def test_danh_sach_va_xoa_job(env):
    job_id = post(env).json()["job_id"]
    lst = env.client.get("/api/stt/jobs").json()
    assert [j["job_id"] for j in lst] == [job_id] and "segments" not in lst[0]
    assert env.client.delete(f"/api/stt/jobs/{job_id}").status_code == 204
    assert env.client.get(f"/api/stt/jobs/{job_id}").status_code == 404


def test_engines_endpoint(env):
    got = env.client.get("/api/stt/engines").json()
    assert got == {"default": "fake", "engines": [{"name": "fake", "available": True}]}


def test_ghi_vet_va_rieng_tu(env):
    job_id = post(env, name="luong-nhan-su-mat.mp3").json()["job_id"]
    (uid, event, detail), = env.audit
    assert (uid, event) == (A.id, "stt_run")
    assert detail["job_id"] == job_id and detail["segments"] == 3 and detail["duration_s"] == FAKE_SECONDS
    assert detail["bytes"] == len(b"AUDIO-GIA")
    assert "luong-nhan-su" not in str(env.audit) and "tiến độ" not in str(env.audit)
    assert env.usage == [(A.id, "fake")]
    assert "luong-nhan-su" not in str(rows(env)[0].__dict__)  # DB không có tên file


def test_van_ban_chuan_hoa_nfc_va_bo_doan_rong(env):
    import unicodedata

    decomposed = unicodedata.normalize("NFD", "Điều khoản")
    env.eng.segments = [Segment(0, 2, f"  {decomposed} "), Segment(2, 3, "   "), Segment(3, 99, "Hết")]
    got = env.client.get(f"/api/stt/jobs/{post(env).json()['job_id']}").json()
    assert [s["text"] for s in got["segments"]] == ["Điều khoản", "Hết"]
    assert got["segments"][0]["text"] == unicodedata.normalize("NFC", got["segments"][0]["text"])
    assert got["segments"][1]["end"] == FAKE_SECONDS  # đoạn quá cuối file bị cắt về thời lượng thật


def test_tien_do_bao_theo_giay(env):
    seen = []
    p = Path(env.tmp)
    p.mkdir(parents=True, exist_ok=True)
    src = p / "src.bin"
    src.write_bytes(b"AUDIO-GIA")
    res = service.transcribe(str(src), progress=lambda done, total: seen.append((done, total)))
    assert seen == [(0.0, 12.0), (4.0, 12.0), (9.5, 12.0), (12.0, 12.0)]
    assert res.duration_s == 12.0 and src.exists()  # service không xóa tệp của người gọi


# ---------- đầu vào bị từ chối ----------

def test_file_khong_phai_am_thanh_bi_tu_choi_ngay(env):
    r = post(env, data=b"BAD!" + b"\x00" * 10, name="trojan.mp3")
    assert r.status_code == 400 and "Không đọc được" in r.json()["detail"]
    assert rows(env) == [] and env.audit == [] and env.eng.calls == 0 and leftovers(env) == []


def test_ghi_am_khai_bao_qua_dai_bi_tu_choi_ngay(env):
    r = post(env, data=b"LONG....")
    assert r.status_code == 422 and "giới hạn" in r.json()["detail"]
    assert rows(env) == [] and leftovers(env) == []


def test_loi_doi_dinh_dang_giua_chung_thanh_failed(env):
    """Probe qua nhưng đổi WAV hỏng / thời lượng thật quá dài (metadata sai): job failed, tệp bị xóa."""
    for head, msg in ((b"BAD2", "Không đọc được"), (b"LON2", "giới hạn")):
        got = env.client.get(f"/api/stt/jobs/{post(env, data=head + b'....').json()['job_id']}").json()
        assert got["status"] == "failed" and msg in got["error"] and got["segments"] is None
    assert [e for _, e, _ in env.audit] == ["stt_job_failed", "stt_job_failed"]
    assert env.eng.calls == 0 and leftovers(env) == []


def test_vuot_dung_luong_413_khong_de_lai_tep(env, monkeypatch):
    monkeypatch.setattr(settings, "stt_max_mb", 0.0001)  # ~100 byte
    r = post(env, data=b"x" * 500)
    assert r.status_code == 413
    assert rows(env) == [] and env.audit == [] and leftovers(env) == []


def test_ten_engine_sai_400_khong_de_lai_tep(env):
    r = post(env, engine="khong-co")
    assert r.status_code == 400 and "Engine không tồn tại" in r.json()["detail"]
    assert rows(env) == [] and env.audit == [] and leftovers(env) == []


def test_chua_cau_hinh_engine_nao(env, monkeypatch):
    monkeypatch.setattr(settings, "stt_engine", "")
    r = post(env)
    assert r.status_code == 400 and "Engine không tồn tại" in r.json()["detail"]
    with pytest.raises(UnknownEngine, match="chưa có engine nào"):
        monkeypatch.setattr("app.stt.engines.ENGINES", {})
        get_engine("x")


def test_engine_tat_503_ngay_khi_tao_job(env):
    env.eng.is_available = False
    r = post(env)
    assert r.status_code == 503 and "chưa sẵn sàng" in r.json()["detail"]
    assert rows(env) == [] and leftovers(env) == []
    assert list_engines() == [{"name": "fake", "available": False}]


def test_thieu_ffmpeg_503(env, monkeypatch):
    from app.stt.errors import EngineUnavailable

    def missing():
        raise EngineUnavailable("Máy chủ chưa cài ffmpeg nên chưa xử lý được ghi âm")

    monkeypatch.setattr(audio, "require_ffmpeg", missing)
    r = post(env)
    assert r.status_code == 503 and "ffmpeg" in r.json()["detail"]
    assert rows(env) == [] and leftovers(env) == []


# ---------- quyền ----------

def test_chu_job_khac_va_admin(env):
    job_id = post(env).json()["job_id"]
    url = f"/api/stt/jobs/{job_id}"
    assert env.client.get(url).status_code == 200
    assert env.audit[-1][1] == "stt_run"  # chủ xem không ghi stt_job_view

    env.who["user"] = B
    assert env.client.get(url).status_code == 404
    assert env.client.delete(url).status_code == 404
    assert env.client.get("/api/stt/jobs").json() == []

    n = len(env.audit)
    env.who["user"] = ADMIN
    assert env.client.get(url).status_code == 200
    (uid, event, detail), = env.audit[n:]
    assert (uid, event) == (ADMIN.id, "stt_job_view") and detail["owner_id"] == A.id
    assert env.client.delete(url).status_code == 404  # admin xem được nhưng không xóa hộ


def test_admin_xem_ma_ghi_vet_loi_thi_khong_tra_noi_dung(env, monkeypatch):
    job_id = post(env).json()["job_id"]

    def broken(*a):
        raise RuntimeError("audit hỏng")

    monkeypatch.setattr(jobs, "_audit", broken)
    env.who["user"] = ADMIN
    client = TestClient(env.client.app, raise_server_exceptions=False)
    r = client.get(f"/api/stt/jobs/{job_id}")
    assert r.status_code == 500 and "Xin chào" not in r.text


def test_job_qua_han_la_khong_ton_tai_va_bi_don(env):
    job_id = post(env).json()["job_id"]
    with env.factory() as db:
        db.get(SttJob, job_id).expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
    assert env.client.get(f"/api/stt/jobs/{job_id}").status_code == 404
    assert env.client.get("/api/stt/jobs").json() == []
    post(env)  # tạo job mới thì dọn job hết hạn
    assert job_id not in [r.id for r in rows(env)]


# ---------- hạn mức ----------

def _seed_active(env, user_id, n, prefix):
    now = datetime.now(UTC)
    with env.factory() as db:
        for i in range(n):
            db.add(SttJob(id=f"{prefix}{i}", user_id=user_id, status="running", engine="fake",
                          created_at=now, expires_at=now + timedelta(days=1)))
        db.commit()


def test_han_muc_moi_nguoi_429(env, monkeypatch):
    monkeypatch.setattr(settings, "stt_job_max_active_per_user", 2)
    _seed_active(env, A.id, 2, "a")
    r = post(env)
    assert r.status_code == 429 and "tối đa 2" in r.json()["detail"]
    assert leftovers(env) == [] and len(rows(env)) == 2
    env.who["user"] = B
    assert post(env).status_code == 202  # hạn mức tính theo từng người


def test_han_muc_toan_he_thong_429(env, monkeypatch):
    monkeypatch.setattr(settings, "stt_job_queue_max", 3)
    _seed_active(env, B.id, 3, "b")
    r = post(env)
    assert r.status_code == 429 and "quá nhiều" in r.json()["detail"] and leftovers(env) == []


# ---------- lỗi và hủy ----------

def test_loi_engine_khong_lo_chi_tiet(env):
    def boom():
        raise RuntimeError("duong dan noi bo C:\\secret")

    env.eng.hook = boom
    got = env.client.get(f"/api/stt/jobs/{post(env).json()['job_id']}").json()
    assert got["status"] == "failed" and "secret" not in got["error"] and "Engine 'fake' lỗi" in got["error"]
    assert [e for _, e, _ in env.audit] == ["stt_job_failed"] and "secret" not in str(env.audit)
    assert leftovers(env) == []


def test_huy_job_dang_chay_dung_worker_xoa_tep_khong_ghi_stt_run(env):
    box = []

    def cancel_midway():
        if len(box) == 1:  # ngay trước đoạn thứ hai
            with env.factory() as db:
                db.delete(db.get(SttJob, box[0]))
                db.commit()

    env.eng.hook = cancel_midway
    orig = jobs._submit
    env.monkeypatch.setattr(jobs, "_submit", lambda fn, jid, *a: (box.append(jid), orig(fn, jid, *a)))
    post(env)
    assert rows(env) == []  # job đã bị xóa, worker không ghi lại
    assert env.audit == [] and env.usage == []
    assert env.eng.closed  # engine được đóng ngay, không chép tiếp
    assert leftovers(env) == []


# ---------- khởi động lại ----------

def test_job_gian_doan_duoc_danh_dau_failed(env):
    now = datetime.now(UTC)
    with env.factory() as db:
        for jid, status in (("q", "queued"), ("r", "running"), ("d", "done")):
            db.add(SttJob(id=jid, user_id=1, status=status, engine="fake", created_at=now,
                          expires_at=now + timedelta(days=1)))
        db.commit()
        assert jobs.recover_interrupted(db) == 2
    by_id = {r.id: r for r in rows(env)}
    assert by_id["q"].status == by_id["r"].status == "failed" and "khởi động lại" in by_id["r"].error
    assert by_id["d"].status == "done"


def test_khoi_dong_don_sach_thu_muc_tam(env):
    env.tmp.mkdir(parents=True, exist_ok=True)
    (env.tmp / "up-mo-coi.bin").write_bytes(b"x")
    (env.tmp / "wav-mo-coi").mkdir()
    (env.tmp / "wav-mo-coi" / "audio.wav").write_bytes(b"x")
    assert files.purge_all() == 2
    assert leftovers(env) == []


# ---------- ffmpeg thật ----------

def tone_wav(path: Path, seconds: float, rate: int = 44_100, channels: int = 2) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(rate)
        n = int(rate * seconds)
        frames = b"".join(
            struct.pack("<h", int(8000 * math.sin(2 * math.pi * 440 * i / rate))) * channels for i in range(n)
        )
        w.writeframes(frames)


@pytest.mark.skipif(not HAVE_FFMPEG, reason="máy không có ffmpeg")
class TestFfmpegThat:
    def test_doi_sang_wav_16k_mono(self, tmp_path):
        src, dst = tmp_path / "in.wav", tmp_path / "out.wav"
        tone_wav(src, 2.0)  # 44,1 kHz stereo -> 16 kHz mono
        seconds = audio.convert(str(src), str(dst), max_seconds=60)
        assert seconds == pytest.approx(2.0, abs=0.05)
        with wave.open(str(dst)) as w:
            assert (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (16_000, 1, 2)

    def test_rac_khong_phai_am_thanh(self, tmp_path):
        src = tmp_path / "trojan.mp3"
        src.write_bytes(b"MZ\x90\x00" + b"\x00" * 200)  # đuôi .mp3 nhưng là mã thực thi
        with pytest.raises(UnsupportedAudio):
            audio.convert(str(src), str(tmp_path / "o.wav"), max_seconds=60)

    def test_probe_nhan_wav_that_va_lay_thoi_luong(self, tmp_path):
        src = tmp_path / "in.wav"
        tone_wav(src, 2.0)
        assert audio.probe(str(src), max_seconds=60) == pytest.approx(2.0, abs=0.1)

    def test_probe_tu_choi_rac_va_file_rong_va_qua_dai(self, tmp_path):
        trojan, empty, long = tmp_path / "t.mp3", tmp_path / "e.mp3", tmp_path / "l.wav"
        trojan.write_bytes(b"MZ\x90\x00" + b"\x00" * 200)
        empty.write_bytes(b"")
        tone_wav(long, 3.0, rate=8000, channels=1)
        for bad in (trojan, empty):
            with pytest.raises(UnsupportedAudio):
                audio.probe(str(bad), max_seconds=60)
        with pytest.raises(AudioTooLong):
            audio.probe(str(long), max_seconds=1)

    def test_file_rong(self, tmp_path):
        src = tmp_path / "empty.mp3"
        src.write_bytes(b"")
        with pytest.raises(UnsupportedAudio):
            audio.convert(str(src), str(tmp_path / "o.wav"), max_seconds=60)

    def test_qua_dai(self, tmp_path):
        src = tmp_path / "in.wav"
        tone_wav(src, 3.0, rate=8000, channels=1)
        with pytest.raises(AudioTooLong, match="giới hạn"):
            audio.convert(str(src), str(tmp_path / "o.wav"), max_seconds=1)

    def test_loi_ffmpeg_khong_lo_duong_dan(self, tmp_path):
        src = tmp_path / "bi-mat-luong.mp3"
        src.write_bytes(b"not audio at all")
        with pytest.raises(UnsupportedAudio) as e:
            audio.convert(str(src), str(tmp_path / "o.wav"), max_seconds=60)
        assert "bi-mat-luong" not in str(e.value) and str(tmp_path) not in str(e.value)

    def test_toan_trinh_qua_api_voi_wav_that(self, env, tmp_path):
        env.monkeypatch.undo()  # bỏ ffmpeg giả (probe/convert/require_ffmpeg); dựng lại phần còn lại
        env.monkeypatch.setattr(settings, "stt_tmp_dir", str(env.tmp))
        env.monkeypatch.setattr(settings, "stt_engine", "fake")
        env.monkeypatch.setattr(jobs, "session_factory", env.factory)
        env.monkeypatch.setattr(jobs, "_audit", lambda *a: None)
        env.monkeypatch.setattr(jobs, "_usage", lambda *a: None)
        env.monkeypatch.setattr(jobs, "_submit", lambda fn, *args: fn(*args))
        env.monkeypatch.setitem(ENGINES, "fake", lambda: env.eng)
        src = tmp_path / "hop.wav"
        tone_wav(src, 1.5)
        r = post(env, data=src.read_bytes(), name="hop.wav", mime="audio/wav")
        assert r.status_code == 202
        got = env.client.get(f"/api/stt/jobs/{r.json()['job_id']}").json()
        assert got["status"] == "done" and got["duration_s"] == pytest.approx(1.5, abs=0.05)
        # engine nhận đúng WAV 16 kHz mono (đã bị xóa sau job nên chỉ kiểm đường dẫn)
        assert env.eng.paths[0].endswith("audio.wav") and leftovers(env) == []
