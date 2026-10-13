import os
import time

from flask import Flask, Response, jsonify, request

from gorev_yoneticisi import Durum

# Şartname madde 10: durum, görev, okunan QR, PLC haberleşme durumu, gelen/giden mesajlar
# ve uzaktan manuel kontrol. İnternet olmayan yarışma ağında çalışsın diye dışarıdan
# hiçbir dosya (CDN, font vb.) kullanılmaz.

DURUM_ETIKET = {
    "IDLE": "Göreve hazır bekleme",
    "GOREV_ISLENIYOR": "Görev alındı, işleniyor",
    "YUKSUZ_HAREKET": "Görev alındı, yüksüz hareket",
    "YUKLU_HAREKET": "Görev alındı, yüklü hareket",
    "KAPI_BEKLENIYOR": "Fabrika otomasyon sistemi komutu bekleniyor",
    "BASLANGICA_DONUS": "Görev tamamlandı, başlangıç noktasına hareket",
    "HATA": "Hata durumu (robotta hata var)",
    "ACIL_STOP": "Acil stop durumu",
}

# Sadece geliştirme sırasında (GELISTIRME=1) açılan test paneli.
# Yarışmada anahtar robot üzerindeki fiziksel anahtardır, arayüzden değiştirilemez.
GELISTIRME = os.environ.get("GELISTIRME") == "1"


def uygulama_olustur(robot, kilit):
    app = Flask(__name__)

    @app.get("/")
    def ana_sayfa():
        return Response(SAYFA, mimetype="text/html")

    @app.get("/api/durum")
    def api_durum():
        with kilit:
            bilgi = robot.durum_bilgisi()
        bilgi["sunucu_zamani"] = time.time()
        bilgi["gelistirme"] = GELISTIRME
        bilgi["durumlar"] = [
            {"kod": d.value, "ad": d.name, "etiket": DURUM_ETIKET[d.name]} for d in Durum
        ]
        return jsonify(bilgi)

    @app.post("/api/komut")
    def api_komut():
        veri = request.get_json(silent=True) or {}
        try:
            sol = max(-255, min(255, int(veri.get("sol", 0))))
            sag = max(-255, min(255, int(veri.get("sag", 0))))
        except (TypeError, ValueError):
            return jsonify(ok=False, mesaj="Geçersiz komut"), 400
        with kilit:
            kabul, neden = robot.uzaktan_komut(sol, sag)
        if not kabul:
            return jsonify(ok=False, mesaj=neden), 403
        return jsonify(ok=True, sol=sol, sag=sag)

    if GELISTIRME:
        @app.post("/api/gelistirme/anahtar")
        def gel_anahtar():
            veri = request.get_json(silent=True) or {}
            with kilit:
                robot.mod_degistir(veri.get("mod", ""))
            return jsonify(ok=True)

        @app.post("/api/gelistirme/qr")
        def gel_qr():
            veri = request.get_json(silent=True) or {}
            with kilit:
                robot.qr_okundu(str(veri.get("veri", "")))
            return jsonify(ok=True)

        @app.post("/api/gelistirme/kill")
        def gel_kill():
            veri = request.get_json(silent=True) or {}
            with kilit:
                if veri.get("basili"):
                    print("!!! Kill switch basıldı (arayüz test paneli)")
                    robot.acil_durdur()
                else:
                    print("Kill switch bırakıldı (arayüz test paneli)")
                    robot.devam_et()
            return jsonify(ok=True)

    return app


SAYFA = r"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Forklift AMR İzleme</title>
<style>
:root{--bg:#f2f5f8;--kart:#fff;--yazi:#1c2733;--soluk:#667483;--cizgi:#dbe2ea;
--mavi:#1f6feb;--yesil:#1a8f4c;--sari:#b7791f;--kirmizi:#c62828;--gri:#7b8794;--acik:#eef2f6}
@media (prefers-color-scheme:dark){
:root{--bg:#10161d;--kart:#18212b;--yazi:#e6edf3;--soluk:#93a1b0;--cizgi:#2a3644;--acik:#212d3a;
--mavi:#58a6ff;--yesil:#3fb96d;--sari:#e3b341;--kirmizi:#ff6b6b;--gri:#8b98a6}}
*{box-sizing:border-box}
[hidden]{display:none!important}
body{margin:0;font:15px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;background:var(--bg);color:var(--yazi)}
header{display:flex;justify-content:space-between;align-items:center;padding:14px 22px;background:var(--kart);border-bottom:1px solid var(--cizgi)}
h1{font-size:18px;margin:0}
main{max-width:1180px;margin:0 auto;padding:18px 22px 40px}
.chip{display:inline-block;padding:3px 11px;border-radius:99px;font-size:13px;font-weight:600;background:var(--acik);color:var(--soluk)}
.chip.iyi{background:color-mix(in srgb,var(--yesil) 18%,transparent);color:var(--yesil)}
.chip.kotu{background:color-mix(in srgb,var(--kirmizi) 18%,transparent);color:var(--kirmizi)}
.chip.uyari{background:color-mix(in srgb,var(--sari) 20%,transparent);color:var(--sari)}
.banner{display:flex;align-items:center;gap:18px;padding:18px 22px;border-radius:14px;color:#fff;background:var(--gri)}
.banner .kod{font-size:38px;font-weight:700;width:64px;height:64px;border-radius:50%;background:rgba(255,255,255,.2);display:flex;align-items:center;justify-content:center}
.banner .etiket{font-size:22px;font-weight:700}
.banner .alt{opacity:.9;margin-top:2px}
.banner.idle{background:#5b6b7b}.banner.hareket{background:#1f6feb}.banner.isleniyor{background:#6f42c1}
.banner.kapi{background:#b7791f}.banner.donus{background:#1a8f4c}.banner.hata,.banner.acil{background:#c62828}
.hata{margin-top:12px;padding:12px 16px;border-radius:10px;background:color-mix(in srgb,var(--kirmizi) 14%,transparent);border:1px solid var(--kirmizi);color:var(--kirmizi);font-weight:600}
.adimlar{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0}
.adim{padding:6px 12px;border-radius:8px;background:var(--kart);border:1px solid var(--cizgi);color:var(--soluk);font-size:13px}
.adim b{margin-right:6px}
.adim.aktif{background:var(--mavi);border-color:var(--mavi);color:#fff}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px}
.kart{background:var(--kart);border:1px solid var(--cizgi);border-radius:12px;padding:16px 18px}
.kart h2{font-size:13px;letter-spacing:.06em;text-transform:uppercase;color:var(--soluk);margin:0 0 12px}
.genis{grid-column:1/-1}
.satir{display:flex;justify-content:space-between;gap:12px;padding:5px 0;border-bottom:1px dashed var(--cizgi)}
.satir:last-child{border-bottom:0}
.satir span:first-child{color:var(--soluk)}
.satir span:last-child{font-weight:600;text-align:right}
.buyuk{font-size:26px;font-weight:700}
.bar{height:8px;border-radius:99px;background:var(--acik);overflow:hidden;margin-top:8px}
.bar i{display:block;height:100%;background:var(--mavi);width:0}
.bar i.asti{background:var(--kirmizi)}
table{width:100%;border-collapse:collapse;font-size:13.5px}
th{text-align:left;color:var(--soluk);font-weight:600;padding:6px 8px;border-bottom:1px solid var(--cizgi)}
td{padding:6px 8px;border-bottom:1px solid var(--cizgi);vertical-align:top}
td.yon-gelen{color:var(--yesil);font-weight:600}td.yon-giden{color:var(--mavi);font-weight:600}
.mesajlar{max-height:300px;overflow:auto}
.surus{display:grid;grid-template-columns:repeat(3,64px);gap:8px;justify-content:center;margin:12px 0}
button{font:inherit;cursor:pointer;border:1px solid var(--cizgi);background:var(--acik);color:var(--yazi);border-radius:9px;padding:9px 12px;font-weight:600}
button:hover:not(:disabled){border-color:var(--mavi)}
button:disabled{opacity:.4;cursor:not-allowed}
button.dur{background:var(--kirmizi);color:#fff;border-color:var(--kirmizi)}
.not{color:var(--soluk);font-size:13px;margin-top:6px}
input[type=text]{font:inherit;padding:8px 10px;border:1px solid var(--cizgi);border-radius:8px;background:var(--bg);color:var(--yazi);width:140px}
.dev{border:2px dashed var(--sari)}
.sag{margin-left:auto}
</style>
</head>
<body>
<header>
  <h1>Forklift AMR · İzleme ve Kontrol</h1>
  <span id="arayuzChip" class="chip">Bağlanıyor…</span>
</header>
<main>
  <section id="banner" class="banner idle">
    <div class="kod" id="durumKod">–</div>
    <div>
      <div class="etiket" id="durumEtiket">Robot durumu bekleniyor</div>
      <div class="alt" id="durumAlt"></div>
    </div>
  </section>
  <div id="hataKutu" class="hata" hidden></div>
  <section class="adimlar" id="adimlar"></section>

  <div class="grid">
    <article class="kart">
      <h2>Görev</h2>
      <div class="satir"><span>Alma → Bırakma</span><span id="gorev" class="buyuk">–</span></div>
      <div class="satir"><span>Yük durumu</span><span id="yuk">–</span></div>
      <div class="satir"><span>Aşama</span><span id="faz">–</span></div>
      <div class="satir"><span>Beklenen QR</span><span id="beklenenQr">–</span></div>
      <div class="satir"><span>Görev süresi</span><span id="sure">–</span></div>
      <div class="bar"><i id="sureBar"></i></div>
      <div class="not">Hedef süre 30 dk. Erken bitiş +1, geç bitiş −1 puan/dk.</div>
    </article>

    <article class="kart">
      <h2>Konum</h2>
      <div class="satir"><span>X (m)</span><span id="konumX">–</span></div>
      <div class="satir"><span>Y (m)</span><span id="konumY">–</span></div>
      <div class="not">Haritalama bağlanana kadar 0,00 gönderilir.</div>
    </article>

    <article class="kart">
      <h2>Okunan QR kod</h2>
      <div class="satir"><span>Son okunan</span><span id="sonQr" class="buyuk">–</span></div>
      <table><thead><tr><th>Zaman</th><th>QR</th><th>Sonuç</th></tr></thead><tbody id="qrTablo"></tbody></table>
    </article>

    <article class="kart">
      <h2>Fabrika otomasyon sistemi (PLC)</h2>
      <div class="satir"><span>Haberleşme</span><span><span id="plcChip" class="chip">–</span></span></div>
      <div class="satir"><span>Adres (UDP)</span><span id="plcAdres">–</span></div>
      <div class="satir"><span>Son cevap</span><span id="plcCevap">–</span></div>
    </article>

    <article class="kart">
      <h2>Mod ve uzaktan kontrol</h2>
      <div class="satir"><span>Robot anahtarı</span><span><span id="modChip" class="chip">–</span></span></div>
      <div class="satir"><span>Son sürüş komutu</span><span id="hedef">–</span></div>
      <div class="surus">
        <span></span><button id="ileri" disabled>▲</button><span></span>
        <button id="sol" disabled>◀</button><button id="dur" class="dur" disabled>■</button><button id="sag" disabled>▶</button>
        <span></span><button id="geri" disabled>▼</button><span></span>
      </div>
      <div class="satir"><span>Hız (0-255)</span><span><input type="range" id="hiz" min="0" max="255" value="100"> <b id="hizDeger">100</b></span></div>
      <div class="not" id="komutDurum">Uzaktan kontrol yalnızca anahtar MANUEL konumdayken çalışır.</div>
    </article>

    <article class="kart dev" id="devKart" hidden>
      <h2>Geliştirme paneli (yarışmada kapalı)</h2>
      <div class="satir"><span>Anahtar (simülasyon)</span>
        <span><button id="devOto">Otomatik</button> <button id="devMan">Manuel</button></span></div>
      <div class="satir"><span>QR gönder</span>
        <span><input type="text" id="devQr" placeholder="ALIM1"> <button id="devQrGonder">Gönder</button></span></div>
      <div class="satir"><span>Acil stop</span>
        <span><button id="devKillAc" class="dur">Bas</button> <button id="devKillBirak">Bırak</button></span></div>
    </article>

    <article class="kart genis">
      <h2>Alınan ve gönderilen mesajlar</h2>
      <div class="mesajlar">
        <table><thead><tr><th>Zaman</th><th>Yön</th><th>Mesaj</th></tr></thead><tbody id="mesajTablo"></tbody></table>
      </div>
    </article>
  </div>
</main>

<script>
const $ = id => document.getElementById(id);
const FAZ = {
  alma_noktasina_gidiyor: "Alma noktasına gidiyor",
  yukleniyor: "Yük alınıyor",
  kapiya_gidiyor: "Kapıya gidiyor",
  birakma_noktasina_gidiyor: "Bırakma noktasına gidiyor",
  birakiyor: "Yük bırakılıyor",
  beklemeye_gidiyor: "Başlangıç noktasına gidiyor"
};
const BANNER = {IDLE:"idle", GOREV_ISLENIYOR:"isleniyor", YUKSUZ_HAREKET:"hareket", YUKLU_HAREKET:"hareket",
  KAPI_BEKLENIYOR:"kapi", BASLANGICA_DONUS:"donus", HATA:"hata", ACIL_STOP:"acil"};
let adimlarKuruldu = false;

function sureYaz(sn){
  const m = Math.floor(sn / 60), s = Math.floor(sn % 60);
  return String(m).padStart(2, "0") + ":" + String(s).padStart(2, "0");
}
function hucre(tr, metin, sinif){
  const td = document.createElement("td");
  td.textContent = metin;
  if (sinif) td.className = sinif;
  tr.appendChild(td);
}
function tabloDoldur(govde, satirlar){
  govde.replaceChildren();
  satirlar.forEach(h => {
    const tr = document.createElement("tr");
    h.forEach(x => hucre(tr, x[0], x[1]));
    govde.appendChild(tr);
  });
}
function chip(el, metin, tur){ el.textContent = metin; el.className = "chip " + (tur || ""); }

function ciz(d){
  if (!adimlarKuruldu){
    d.durumlar.forEach(x => {
      const e = document.createElement("div");
      e.className = "adim"; e.id = "adim" + x.kod;
      const b = document.createElement("b"); b.textContent = x.kod;
      e.appendChild(b); e.appendChild(document.createTextNode(x.etiket));
      $("adimlar").appendChild(e);
    });
    adimlarKuruldu = true;
  }
  const bilgi = d.durumlar.find(x => x.kod === d.durum_kodu);
  $("banner").className = "banner " + (BANNER[d.durum] || "idle");
  $("durumKod").textContent = d.durum_kodu;
  $("durumEtiket").textContent = bilgi ? bilgi.etiket : d.durum;
  $("durumAlt").textContent = d.faz ? (FAZ[d.faz] || d.faz) : "";
  d.durumlar.forEach(x => $("adim" + x.kod).classList.toggle("aktif", x.kod === d.durum_kodu));

  $("hataKutu").hidden = !d.hata;
  $("hataKutu").textContent = d.hata ? "HATA: " + d.hata : "";

  $("gorev").textContent = d.gorev ? "A" + d.gorev.alim + " → B" + d.gorev.birakma : "Görev yok";
  $("yuk").textContent = d.gorev ? (d.yuklu ? "Yüklü" : "Yüksüz") : "–";
  $("faz").textContent = d.faz ? (FAZ[d.faz] || d.faz) : "–";
  $("beklenenQr").textContent = d.beklenen_qr || "–";
  $("sure").textContent = d.gorev ? sureYaz(d.gecen_sure_sn) + " / " + sureYaz(d.hedef_sure_sn) : "–";
  const oran = d.gorev ? Math.min(100, d.gecen_sure_sn / d.hedef_sure_sn * 100) : 0;
  $("sureBar").style.width = oran + "%";
  $("sureBar").className = (d.gorev && d.gecen_sure_sn > d.hedef_sure_sn) ? "asti" : "";

  $("konumX").textContent = d.konum[0].toFixed(2);
  $("konumY").textContent = d.konum[1].toFixed(2);

  $("sonQr").textContent = d.son_qr || "–";
  tabloDoldur($("qrTablo"), d.qr_gecmisi.slice().reverse().slice(0, 8).map(q =>
    [[q.zaman], [q.veri], [q.sonuc, q.sonuc === "doğrulandı" ? "yon-gelen" : ""]]));

  chip($("plcChip"), d.plc_bagli ? "Bağlı" : "Bağlantı yok", d.plc_bagli ? "iyi" : "kotu");
  $("plcAdres").textContent = d.plc_adres || "–";
  $("plcCevap").textContent = d.plc_son_cevap
    ? Math.max(0, d.sunucu_zamani - d.plc_son_cevap).toFixed(1) + " sn önce" : "henüz cevap yok";

  const manuel = d.mod === "manuel";
  chip($("modChip"), manuel ? "MANUEL" : "OTOMATİK", manuel ? "uyari" : "iyi");
  $("hedef").textContent = "V," + d.uzaktan_hedef[0] + "," + d.uzaktan_hedef[1];
  const aktif = manuel && d.durum !== "ACIL_STOP";
  ["ileri", "geri", "sol", "sag", "dur"].forEach(id => $(id).disabled = !aktif);
  if (!aktif && $("komutDurum").dataset.mesaj !== "1")
    $("komutDurum").textContent = d.durum === "ACIL_STOP"
      ? "Acil stop aktif, uzaktan kontrol kapalı."
      : "Anahtar OTOMATİK konumda, uzaktan kontrol kapalı.";

  tabloDoldur($("mesajTablo"), d.mesajlar.slice().reverse().map(m =>
    [[m.zaman], [m.yon === "gelen" ? "← PLC'den" : "→ PLC'ye", "yon-" + m.yon], [m.metin]]));

  $("devKart").hidden = !d.gelistirme;
}

async function yenile(){
  try {
    const r = await fetch("/api/durum", {cache: "no-store"});
    ciz(await r.json());
    chip($("arayuzChip"), "Robota bağlı", "iyi");
  } catch (e) {
    chip($("arayuzChip"), "Robota ulaşılamıyor", "kotu");
  }
}

async function postla(url, govde){
  const r = await fetch(url, {method: "POST", headers: {"Content-Type": "application/json"},
                              body: JSON.stringify(govde)});
  return r.json().catch(() => ({}));
}
async function komut(sol, sag){
  const j = await postla("/api/komut", {sol, sag});
  $("komutDurum").dataset.mesaj = "1";
  $("komutDurum").textContent = j.ok ? "Gönderildi: V," + sol + "," + sag : (j.mesaj || "Reddedildi");
  setTimeout(() => { $("komutDurum").dataset.mesaj = "0"; }, 3000);
  yenile();
}
const hiz = () => parseInt($("hiz").value, 10);
$("hiz").oninput = () => { $("hizDeger").textContent = $("hiz").value; };
$("ileri").onclick = () => komut(hiz(), hiz());
$("geri").onclick = () => komut(-hiz(), -hiz());
$("sol").onclick = () => komut(-hiz(), hiz());
$("sag").onclick = () => komut(hiz(), -hiz());
$("dur").onclick = () => komut(0, 0);

$("devOto").onclick = async () => { await postla("/api/gelistirme/anahtar", {mod: "otomatik"}); yenile(); };
$("devMan").onclick = async () => { await postla("/api/gelistirme/anahtar", {mod: "manuel"}); yenile(); };
$("devQrGonder").onclick = async () => {
  const v = $("devQr").value.trim();
  if (v) { await postla("/api/gelistirme/qr", {veri: v}); $("devQr").value = ""; yenile(); }
};
$("devQr").onkeydown = e => { if (e.key === "Enter") $("devQrGonder").click(); };
$("devKillAc").onclick = async () => { await postla("/api/gelistirme/kill", {basili: true}); yenile(); };
$("devKillBirak").onclick = async () => { await postla("/api/gelistirme/kill", {basili: false}); yenile(); };

setInterval(yenile, 500);
yenile();
</script>
</body>
</html>
"""