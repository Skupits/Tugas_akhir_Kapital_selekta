import os
import re
import time
import pandas as pd
from collections import Counter
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()
HF_TOKEN = os.getenv("HF_TOKEN")
IG_USER  = os.getenv("IG_USER")
IG_PASS  = os.getenv("IG_PASS")

NEWS_URLS = [
    'https://money.kompas.com/read/2026/06/04/085746426/rupiah-tembus-rp-18000-per-dollar-as-terlemah-sepanjang-sejarah',
]

IG_POST_URLS = [
    'https://www.instagram.com/p/DZJcFuDympN/?utm_source=ig_web_copy_link&igsh=MzRlODBiNWFlZA==',
    'https://www.instagram.com/p/DZHBpRBSpbX/?utm_source=ig_web_copy_link&igsh=MzRlODBiNWFlZA==',
]

# ══════════════════════════════════════════════
# KONFIGURASI SCRAPING KOMENTAR
# ══════════════════════════════════════════════
MAX_STALE_ROUNDS    = 50    # stop per-post jika komentar tidak bertambah selama N round scroll
SCROLL_PAUSE        = 5.0   # detik jeda antar scroll (naikkan jika koneksi lambat)
CHECKPOINT_EVERY    = 100   # simpan ke CSV setiap N komentar baru
TOP_N_KEYWORDS      = 20

STOPWORDS = {
    "dan","yang","di","ke","dari","ini","itu","untuk","pada","dengan","adalah","sebagai",
    "bahwa","dalam","oleh","akan","bisa","ada","tidak","juga","sudah","tersebut","karena",
    "rp","dollar","dolar","juta","miliar","triliun","atau","tetapi","namun","hingga","serta",
    "telah","sedang","masih","seperti","lebih","antara","belum","saat","sangat","setelah",
    "sebelum","ketika","kalau","maka","bagi","pun","agar","atas","kami","kita","mereka",
    "para","pula","yaitu","saja","tapi","jika","bila","meski","tiap","setiap",
}

UI_TEXTS = [
    'balas','suka','lihat terjemahan','hari yang lalu','view all','replies',
    'likes','jam yang lalu','menit yang lalu','detik yang lalu','seminggu yang lalu',
    'sebulan yang lalu','see translation','like','reply','follow',
]


# ─────────────────────────────────────────────
# HELPER: build Selenium driver
# ─────────────────────────────────────────────
def _build_driver(headless=False):
    import undetected_chromedriver as uc
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    if headless:
        options.add_argument("--headless=new")
    return uc.Chrome(options=options, version_main=148)


# ─────────────────────────────────────────────
# HELPER: klik semua tombol "lihat balasan" / "load more"
# ─────────────────────────────────────────────
def _expand_replies(driver):
    """
    Klik semua tombol expand (balasan, load more comments) yang ada di viewport.
    Dijalankan setelah setiap batch scroll.
    """
    from selenium.webdriver.common.by import By
    expand_xpaths = [
        # Tombol "X balasan" / "View N replies"
        "//span[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'balasan')]/..",
        "//span[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'replies')]/..",
        # Tombol "Muat lebih banyak komentar" / "Load more comments"
        "//span[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'muat lebih')]/..",
        "//span[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'load more')]/..",
    ]
    clicked = 0
    for xpath in expand_xpaths:
        try:
            buttons = driver.find_elements(By.XPATH, xpath)
            for btn in buttons:
                try:
                    driver.execute_script("arguments[0].click();", btn)
                    clicked += 1
                    time.sleep(0.4)
                except Exception:
                    pass
        except Exception:
            pass
    return clicked


# ─────────────────────────────────────────────
# HELPER: parse komentar dari page_source saat ini
# ─────────────────────────────────────────────
def _parse_comments(page_source):
    soup  = BeautifulSoup(page_source, 'html.parser')
    spans = soup.find_all('span', dir='auto')
    found = set()
    for span in spans:
        c = span.get_text().strip()
        if not c or len(c.split()) < 2:
            continue
        if any(ui in c.lower() for ui in UI_TEXTS):
            continue
        # Filter: minimal 3 kata, bukan emoji-only, bukan angka doang
        alpha_ratio = sum(ch.isalpha() for ch in c) / max(len(c), 1)
        if alpha_ratio < 0.3:
            continue
        found.add(c)
    return found


# ══════════════════════════════════════════════
# 1. SCRAPE ARTIKEL BERITA
# ══════════════════════════════════════════════
def scrape_articles(urls):
    print("\n[1] SCRAPING ARTIKEL BERITA (via Selenium)...")
    driver       = _build_driver(headless=True)
    article_rows = []
    article_data = []

    for url in urls:
        print(f"  -> {url}")
        try:
            driver.get(url)
            time.sleep(5)
            soup   = BeautifulSoup(driver.page_source, 'html.parser')
            title  = soup.find('h1').get_text(strip=True) if soup.find('h1') else "N/A"
            source = url.split('/')[2]

            body = (
                soup.find('div', class_='detail__body itp_bodycontent_wrapper') or
                soup.find('div', class_='detail__body') or
                soup.find('div', class_='read__content') or
                soup.find('div', {'itemprop': 'articleBody'}) or
                soup.find('article')
            )

            if body:
                full_text = body.get_text(separator=' ').strip()
                status = "OK"
            else:
                paras     = [p.get_text().strip() for p in soup.find_all('p') if len(p.get_text().strip()) > 60]
                full_text = ' '.join(paras)
                status    = "FALLBACK_P" if paras else "GAGAL"

            print(f"  {'✅' if status=='OK' else '⚠️'} {status}: {title[:65]}...")

            kalimat_list = [
                k.strip() for k in re.split(r'(?<=[.!?])\s+|\n', full_text)
                if len(k.strip()) > 20
            ]
            article_rows.append({"url": url, "source": source, "judul": title,
                                  "isi_mentah": full_text, "status": status})
            article_data.append({"url": url, "source": source, "judul": title,
                                  "kalimat_list": kalimat_list, "full_text": full_text})
        except Exception as e:
            print(f"  ❌ Error: {e}")
            article_rows.append({"url": url, "source": url.split('/')[2],
                                  "judul": "[ERROR]", "isi_mentah": str(e), "status": "ERROR"})

    driver.quit()
    pd.DataFrame(article_rows).to_csv("artikel_berita_mentah.csv", index=False, encoding='utf-8-sig')
    print("  📄 artikel_berita_mentah.csv tersimpan")
    return article_data


# ══════════════════════════════════════════════
# 2. EKSTRAK KATA KUNCI NARASI MEDIA
# ══════════════════════════════════════════════
def extract_keywords(article_data, top_n=TOP_N_KEYWORDS):
    print(f"\n[2] EKSTRAK KATA KUNCI NARASI MEDIA (top {top_n})...")
    all_text = " ".join(d["full_text"].lower() for d in article_data if d.get("full_text"))
    words    = [w for w in all_text.split() if w.isalpha() and w not in STOPWORDS and len(w) > 3]
    top_words = Counter(words).most_common(top_n)

    df_kw = pd.DataFrame(top_words, columns=["kata_kunci", "frekuensi"])
    df_kw.insert(0, "rank", range(1, len(df_kw) + 1))
    df_kw.to_csv("kata_kunci_narasi_media.csv", index=False, encoding='utf-8-sig')
    print("  📄 kata_kunci_narasi_media.csv tersimpan")

    print(f"\n  Top {top_n} Kata Kunci Narasi Media:")
    for _, r in df_kw.iterrows():
        print(f"   {r['rank']:2}. {r['kata_kunci']}: {r['frekuensi']}")

    return [kw for kw, _ in top_words]


# ══════════════════════════════════════════════
# 3. SENTIMEN KALIMAT ARTIKEL (filtered by kata kunci)
# ══════════════════════════════════════════════
def run_sentiment_artikel(article_data, keyword_list):
    print(f"\n[3] SENTIMEN KALIMAT ARTIKEL (kata kunci: {', '.join(keyword_list[:5])}...)")

    try:
        from transformers import pipeline
        id_model  = pipeline("text-classification",
                             model="crypter70/IndoBERT-Sentiment-Analysis",
                             token=HF_TOKEN, device=-1)
    except Exception as e:
        print(f"  ❌ Gagal load IndoBERT: {e}"); return

    label_map = {"LABEL_0": "negative", "LABEL_1": "positive"}
    results   = []

    for art in article_data:
        count = 0
        for kalimat in art.get("kalimat_list", []):
            match = [kw for kw in keyword_list if kw in kalimat.lower()]
            if not match:
                continue
            try:
                res  = id_model(kalimat[:512])[0]
                sent = label_map.get(res["label"], res["label"].lower())
                conf = round(res["score"], 4)
            except Exception:
                sent, conf = "error", 0.0
            results.append({
                "source": art["source"], "judul": art["judul"],
                "kalimat": kalimat, "kata_kunci_match": ", ".join(match),
                "jumlah_kw_match": len(match), "sentimen": sent, "confidence": conf,
            })
            count += 1
        print(f"  ✅ {art['source']}: {count} kalimat relevan dianalisis")

    df = pd.DataFrame(results)
    df.to_csv("hasil_sentimen_artikel.csv", index=False, encoding='utf-8-sig')
    print(f"\n  📄 hasil_sentimen_artikel.csv tersimpan ({len(df)} baris)")

    if not df.empty:
        print("\n  RINGKASAN SENTIMEN PER KATA KUNCI:")
        print(f"  {'KATA KUNCI':<20} {'POS':>5} {'NEG':>5} {'TOTAL':>7}")
        print("  " + "-"*40)
        for kw in keyword_list:
            sub = df[df["kata_kunci_match"].str.contains(kw, na=False)]
            pos, neg = (sub["sentimen"]=="positive").sum(), (sub["sentimen"]=="negative").sum()
            if pos + neg > 0:
                print(f"  {kw:<20} {pos:>5} {neg:>5} {pos+neg:>7}")


# ══════════════════════════════════════════════
# 4. SCRAPE KOMENTAR IG — UNLIMITED, PER POST
# ══════════════════════════════════════════════
def scrape_ig_comments(urls):
    """
    Sedot SEMUA komentar yang tersedia dari tiap postingan IG.
    Strategi:
      • Scroll div komentar terus-menerus sampai tidak ada komentar baru
        (deteksi via MAX_STALE_ROUNDS)
      • Setiap batch scroll → klik semua tombol 'lihat balasan' (_expand_replies)
        supaya reply ikut tersedot
      • Dedup global pakai set()
      • Checkpoint CSV per CHECKPOINT_EVERY komentar BARU yang ditemukan
      • Tidak ada hard limit total — berhenti sendiri ketika IG tidak load lagi
    """
    print("\n[4] SCRAPING KOMENTAR IG (UNLIMITED — sedot semaksimal mungkin)...")

    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    driver = _build_driver(headless=False)
    wait   = WebDriverWait(driver, 20)

    # ── Login ──
    driver.get('https://www.instagram.com/accounts/login/')
    try:
        inputs = wait.until(EC.presence_of_all_elements_located((By.TAG_NAME, 'input')))
        inputs[0].send_keys(IG_USER)
        inputs[1].send_keys(IG_PASS + Keys.RETURN)
        time.sleep(8)
        print("  ✅ Login berhasil")
    except Exception as e:
        print(f"  ❌ Login gagal: {e}")
        driver.quit()
        return

    # CSV output — lanjutkan kalau sudah ada (resume support)
    csv_out = "hasil_scraping_komentar_ig.csv"
    global_seen = set()   # dedup lintas post

    if os.path.exists(csv_out):
        df_existing = pd.read_csv(csv_out)
        global_seen = set(df_existing["comment"].tolist())
        print(f"  ↩️  Resume: {len(global_seen)} komentar lama sudah ada di CSV")
    else:
        pd.DataFrame(columns=["post_url","comment"]).to_csv(csv_out, index=False, encoding='utf-8-sig')

    total_saved = len(global_seen)
    buffer      = []   # buffer sebelum di-flush ke CSV

    for post_url in urls:
        print(f"\n  ══ POST: {post_url}")
        driver.get(post_url)
        time.sleep(6)

        # Coba dapat div komentar yang bisa di-scroll
        scroll_div = None
        try:
            scroll_div = WebDriverWait(driver, 8).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, 'div.x5yr21d.xw2csxc.x1odjw0f.x1n2onr6')
                )
            )
            print("  ✅ Scroll div ditemukan")
        except Exception:
            print("  ⚠️  Scroll div tidak ketemu — pakai window scroll")

        post_comments = set()   # komentar dari post ini saja
        stale_rounds  = 0
        round_num     = 0

        while True:
            round_num += 1
            prev_count = len(post_comments)

            # ── Scroll ──
            if scroll_div:
                try:
                    driver.execute_script(
                        "arguments[0].scrollTop = arguments[0].scrollHeight", scroll_div
                    )
                except Exception:
                    # Div mungkin sudah stale, fallback ke window
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            else:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

            time.sleep(SCROLL_PAUSE)

            # ── Expand balasan setiap 5 round ──
            if round_num % 5 == 0:
                clicked = _expand_replies(driver)
                if clicked:
                    time.sleep(1.5)   # beri waktu balasan load

            # ── Parse komentar baru ──
            fresh = _parse_comments(driver.page_source)
            post_comments.update(fresh)

            new_this_round = len(post_comments) - prev_count

            # ── Buffer & checkpoint ──
            for c in fresh:
                if c not in global_seen:
                    global_seen.add(c)
                    buffer.append({"post_url": post_url, "comment": c})

            if len(buffer) >= CHECKPOINT_EVERY:
                df_buf = pd.DataFrame(buffer)
                df_buf.to_csv(csv_out, mode='a', header=False, index=False, encoding='utf-8-sig')
                total_saved += len(buffer)
                print(f"    [CHECKPOINT] +{len(buffer)} → total tersimpan: {total_saved} | "
                      f"post ini: {len(post_comments)} | round: {round_num}")
                buffer = []

            # ── Deteksi stale ──
            if new_this_round == 0:
                stale_rounds += 1
            else:
                stale_rounds = 0

            if stale_rounds >= MAX_STALE_ROUNDS:
                print(f"    ⛔ Tidak ada komentar baru selama {MAX_STALE_ROUNDS} round — "
                      f"post ini selesai ({len(post_comments)} komentar)")
                break

        # Flush sisa buffer setelah selesai 1 post
        if buffer:
            pd.DataFrame(buffer).to_csv(csv_out, mode='a', header=False,
                                        index=False, encoding='utf-8-sig')
            total_saved += len(buffer)
            buffer = []

        print(f"  📌 Selesai post ini: {len(post_comments)} komentar unik")

    driver.quit()
    print(f"\n  ✅ SCRAPING IG SELESAI — Total tersimpan: {total_saved} komentar")
    print(f"  📄 {csv_out}")


# ══════════════════════════════════════════════
# 5. SENTIMEN KOMENTAR IG (IndoBERT + checkpoint)
# ══════════════════════════════════════════════
def run_sentiment_komentar():
    """
    Baca hasil_scraping_komentar_ig.csv → jalankan IndoBERT → simpan hasil_sentimen_publik.csv
    Mendukung resume: kalau hasil_sentimen_publik.csv sudah ada, lanjut dari index terakhir.
    """
    src_csv = "hasil_scraping_komentar_ig.csv"
    out_csv = "hasil_sentimen_publik.csv"

    if not os.path.exists(src_csv):
        print(f"\n  ⚠️ {src_csv} tidak ditemukan. Jalankan scraping dulu.")
        return

    df_all   = pd.read_csv(src_csv)
    comments = df_all["comment"].dropna().tolist()
    post_urls= df_all["post_url"].tolist()
    print(f"\n[5] SENTIMEN {len(comments)} KOMENTAR IG (IndoBERT)...")

    try:
        from transformers import pipeline
        id_model = pipeline("text-classification",
                            model="crypter70/IndoBERT-Sentiment-Analysis",
                            token=HF_TOKEN, device=-1)
    except Exception as e:
        print(f"  ❌ Gagal load IndoBERT: {e}"); return

    label_map = {"LABEL_0": "negative", "LABEL_1": "positive"}

    # Resume support
    if not os.path.exists(out_csv):
        pd.DataFrame(columns=["index","post_url","comment","sentiment","confidence"]).to_csv(
            out_csv, index=False, encoding='utf-8-sig'
        )
        start_idx = 0
    else:
        df_done   = pd.read_csv(out_csv)
        start_idx = len(df_done)
        print(f"  ↩️  Resume dari index ke-{start_idx}...")

    buffer = []
    for i in range(start_idx, len(comments)):
        c = comments[i]
        try:
            res  = id_model(str(c)[:512])[0]
            sent = label_map.get(res["label"], res["label"].lower())
            conf = round(res["score"], 4)
        except Exception:
            sent, conf = "error", 0.0

        buffer.append({
            "index"     : i,
            "post_url"  : post_urls[i] if i < len(post_urls) else "",
            "comment"   : c,
            "sentiment" : sent,
            "confidence": conf,
        })

        if len(buffer) >= CHECKPOINT_EVERY or (i + 1) == len(comments):
            pd.DataFrame(buffer).to_csv(out_csv, mode='a', header=False,
                                        index=False, encoding='utf-8-sig')
            done = start_idx + i - start_idx + 1
            pct  = done / len(comments) * 100
            print(f"  [CHECKPOINT] {done}/{len(comments)} ({pct:.1f}%) selesai.")
            buffer = []

    print(f"\n  ✅ {out_csv} tersimpan ({len(comments)} komentar)")


# ══════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 65)
    print("  ANALISIS SENTIMEN PUBLIK — RUPIAH Rp18.000/USD")
    print("=" * 65)

    # 1 — Scrape artikel
    article_data = scrape_articles(NEWS_URLS)

    # 2 — Ekstrak kata kunci narasi media
    keyword_list = extract_keywords(article_data)

    # 3 — Sentimen kalimat artikel (filtered by kata kunci)
    run_sentiment_artikel(article_data, keyword_list)

    # 4 — Scrape komentar IG (unlimited, per post, dengan expand balasan)
    scrape_ig_comments(IG_POST_URLS)

    # 5 — Sentimen komentar IG
    run_sentiment_komentar()

    print("\n" + "=" * 65)
    print("  OUTPUT FILES:")
    print("  📄 artikel_berita_mentah.csv         → teks mentah artikel")
    print("  📄 kata_kunci_narasi_media.csv        → top kata kunci narasi")
    print("  📄 hasil_sentimen_artikel.csv         → sentimen kalimat artikel")
    print("  📄 hasil_scraping_komentar_ig.csv     → raw komentar IG (semua)")
    print("  📄 hasil_sentimen_publik.csv          → sentimen komentar IG")
    print("=" * 65)