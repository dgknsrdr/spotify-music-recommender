# Spotify Müzik Keşif & Öneri Sistemi 🎵

Bu proje; **Flask**, **PostgreSQL** ve **Scikit-Learn** kullanılarak geliştirilmiş, **Spotify Web API** ile desteklenen uçtan uca (end-to-end) bir müzik öneri web uygulamasıdır. 

Sistem, büyük ölçekli müzik veri setlerini işler, veri temizleme ve matematiksel ölçeklendirme adımlarını uygular, kural tabanlı bir dil algılama mekanizması çalıştırır ve içerik tabanlı filtreleme (Cosine Similarity) kullanarak kullanıcıya özel kişiselleştirilmiş şarkı önerileri sunar.

---

## 🚀 Öne Çıkan Özellikler

### 1. Veri Mühendisliği Süreçleri (`model_hazirlik.py`)
* **Veri Temizleme:** Eksik veriler ve tekrar eden mükerrer şarkılar temizlenmiştir.
* **Akıllı Dil Haritalaması (Türkçe Sanatçı Filtresi):** Regex ile Türkçe karakter kontrolü, ana sanatçı analizi ve popüler Türk Rap/Trap sanatçılarına (Uzi, Motive, Ceg vb.) özel filtreler birleştirilerek hibrit bir dil tespit hattı kurulmuştur. Hibrit yapının yetersiz kaldığı küresel şarkılarda ise `langdetect` kütüphanesine başvurulmuştur.
* **Matematiksel Ölçeklendirme:** Şarkıların sayısal özellikleri (`loudness`, `tempo`, `duration_ms`, `popularity`, `key`) Scikit-Learn kütüphanesinin `MinMaxScaler` fonksiyonu ile normalize edilmiştir.
* **Veritabanı Yönetimi:** İşlenen büyük veri, `SQLAlchemy` aracılığıyla parçalar halinde (chunk-size) yerel **PostgreSQL** veritabanına aktarılmıştır.

### 2. Akıllı Öneri Motoru & Web Arayüzü (`main.py`)
* **Çift Arama Modu:** * **Şarkıya Göre Öneri:** Aranan şarkının akustik özelliklerine göre Cosine Similarity (Kosinüs Benzerliği) algoritması çalıştırılır; dil uyumu ve popülerlik dengesi gözetilerek en benzer 5 şarkı listelenir.
  * **Doğrudan Sanatçı Arama:** Doğrudan yerel PostgreSQL veritabanından veri çekilir. Sayfa yüklenme hızını 0 saniyeye indirmek (optimizasyon) adına, sanatçı görselleri Spotify API'den tek bir toplu istekte çekilerek önbelleğe alınır.
* **Gelişmiş Arayüz:** Spotify estetiğine uygun, Bootstrap 5 ile tasarlanmış modern Glassmorphic (cam efektli) arayüz ve entegre şarkı önizleme (audio preview) desteği.

---

## 🛠️ Kullanılan Teknolojiler

* **Backend:** Python, Flask
* **Veritabanı:** PostgreSQL, SQLAlchemy
* **Veri Bilimi & Yapay Zeka:** Pandas, NumPy, Scikit-Learn (MinMaxScaler, Cosine Similarity)
* **API Entegrasyonu:** Spotipy (Spotify Web API)
* **Frontend:** HTML5, CSS3, Bootstrap 5

---

## 📦 Kurulum ve Çalıştırma

### 1. Veritabanı Hazırlığı
Bilgisayarınızda **PostgreSQL**'in kurulu ve çalışır olduğundan emin olun. `music_db` adında bir veritabanı oluşturun.

### 2. Projeyi Klonlayın
```bash
git clone [https://github.com/kullanici_adin/spotify-music-recommender.git](https://github.com/kullanici_adin/spotify-music-recommender.git)
cd spotify-music-recommender