"""Sahneleri aynı anda birden fazla süreçte render eder.

matplotlib tek iş parçacıklıdır; bir sahne bir çekirdeği doldurur. Sahneler birbirinden bağımsız olduğu için her biri
ayrı bir süreçte (spawn) çizilir, en uzun sahneler önce başlar. Her sahnenin ffmpeg'i birkaç iş parçacığıyla sınırlanır;
yoksa her kodlayıcı bütün çekirdekleri isteyip birbirini boğar. İlerleme bir kuyrukla ana sürece gelir ve toplam kare
oranı olarak bildirilir."""
import multiprocessing as mp
import os
import queue as queue_mod
from concurrent.futures import FIRST_EXCEPTION, ProcessPoolExecutor, wait

FFMPEG_THREADS = 2  # paralel kipte sahne başına kodlayıcı iş parçacığı
REPORT_EVERY = 10   # işçiler her 10 karede bir ilerleme yollar

_queue = None


def auto_workers(n_scenes):
    """Varsayılan işçi sayısı: mantıksal işlemci sayısının yarısı (her sahne bir çekirdek + kodlayıcısı), en fazla
    sahne sayısı kadar."""
    return max(1, min(n_scenes, (os.cpu_count() or 2) // 2))


def _init(q):
    global _queue
    _queue = q


def _render_one(i, scene_type, params, path, transparent):
    from engine import render
    from scenes import REGISTRY

    last = [0]

    def progress(frame, total):
        if frame == total or frame - last[0] >= REPORT_EVERY:
            last[0] = frame
            _queue.put((i, frame, total))

    render.render_video(REGISTRY[scene_type], params, path, transparent, on_progress=progress, threads=FFMPEG_THREADS)
    return i


def render_scenes(jobs, transparent, workers, emit):
    """jobs: [(sıra, sahne tipi, ayarlar, çıktı yolu, kare sayısı)]. Hepsi bitince döner; bir sahne hata verirse diğerleri
    durdurulur ve hata yükselir. progress olayları: scene/frame/total son bildiren sahnenin, overall toplam kare oranı
    (0–1), finished biten sahne sayısı."""
    ctx = mp.get_context("spawn")
    q = ctx.Queue()
    n = len(jobs)
    totals = {j[0]: j[4] for j in jobs}
    frames = dict.fromkeys(totals, 0)
    all_frames = max(sum(totals.values()), 1)
    finished = set()
    ex = ProcessPoolExecutor(max_workers=workers, mp_context=ctx, initializer=_init, initargs=(q,))
    futures = {}
    try:
        for i, scene_type, params, path, _ in sorted(jobs, key=lambda j: -j[4]):   # en uzun sahne önce
            futures[ex.submit(_render_one, i, scene_type, params, path, transparent)] = i
        pending = set(futures)

        last = [(0, 0, totals[0] if 0 in totals else 1)]

        def drain(final=False):
            got = False
            while True:
                try:
                    i, f, t = q.get_nowait()
                except queue_mod.Empty:
                    break
                frames[i] = f
                last[0] = (i, f, t)
                got = True
            if got or final:
                i, f, t = last[0]
                overall = 1.0 if final else round(sum(frames.values()) / all_frames, 4)
                emit(event="progress", scene=i, scenes=n, frame=f, total=t, overall=overall, finished=len(finished))

        while pending:
            done, pending = wait(pending, timeout=0.25, return_when=FIRST_EXCEPTION)
            for fut in done:
                fut.result()   # sahne hata verdiyse burada yükselir
                finished.add(futures[fut])
            drain()
        drain(final=True)   # son olay: hepsi bitti (kuyruktaki son kareler ve biten sahne sayısı eşitlenir)
    except BaseException:
        procs = list((getattr(ex, "_processes", None) or {}).values())   # shutdown bu tabloyu boşaltır; önce al
        ex.shutdown(wait=False, cancel_futures=True)
        for p in procs:   # süren sahneleri beklemeden durdur
            p.terminate()
        raise
    ex.shutdown(wait=True)
