import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sklearn.preprocessing import MinMaxScaler
from langdetect import detect

print("1. Büyük veri seti yükleniyor...")
useful_cols = [
	'id', 'name', 'popularity', 'duration_ms', 'explicit', 'artists',
	'danceability', 'energy', 'key', 'loudness', 'mode',
	'speechiness', 'acousticness', 'instrumentalness', 'liveness', 'valence', 'tempo'
]
df = pd.read_csv('tracks.csv', usecols=useful_cols)

print("2. Ön temizlik yapılıyor...")
df.dropna(subset=['name', 'artists'], inplace=True)
df.drop_duplicates(subset=['name', 'artists'], keep='first', inplace=True)
df['explicit'] = df['explicit'].astype(int)

print("3. AKILLI TÜRKÇE SANATÇI HARİTALAMASI BAŞLADI...")


# Adım A: Temiz ve benzersiz sanatçı isimlerini bulmak için fonksiyon
def get_main_artist(artist_str):
	return artist_str.replace("[", "").replace("]", "").replace("'", "").split(",")[0].strip().lower()


df['main_artist'] = df['artists'].apply(get_main_artist)

# Adım B: İçinde net Türkçe karakter barındıran tüm şarkıları bul ve o sanatçıları "Türk Sanatçı" ilan et!
turkish_chars = "çğıöşü"
tr_artists_set = set(df[df['name'].str.lower().str.contains(f"[{turkish_chars}]", regex=True)]['main_artist'].unique())


print(f"Sistem tarafından otomatik doğrulanan Türk sanatçı/grup sayısı: {len(tr_artists_set)}")

# Adım C: Tüm veri setine dil etiketlerini basıyoruz
languages = []
counter = 0
total = len(df)

for idx, row in df.iterrows():
	counter += 1
	if counter % 50000 == 0:
		print(f"İlerleme: %{(counter / total) * 100:.2f} ({counter}/{total} şarkı etiketlendi)")

	current_artist = row['main_artist']
	current_name = str(row['name']).lower()

	# 1. Kural: Eğer şarkıyı söyleyen sanatçı bizim Türk sanatçılar kümesindeyse, şarkı adı ne olursa olsun  direkt 'tr' yap!
	if current_artist in tr_artists_set:
		languages.append('tr')

	# 2. Kural: Sanatçı listede yoksa ama şarkı isminde Türkçe karakter varsa yine 'tr' yap!
	elif any(char in turkish_chars for char in current_name):
		languages.append('tr')

	# 3. Kural: Yukarıdakilere uymuyorsa yapay zeka kütüphanesine sor (İngilizce, Rusça vb. ayırsın)
	else:
		try:
			lang = detect(current_name)
			languages.append(lang)
		except:
			languages.append('en')

# Yeni sütunu ekle ve geçici sütunu sil
df['language'] = languages
df.drop(columns=['main_artist'], inplace=True)
print("4. Matematiksel Ölçeklendirme uygulanıyor...")
scaler = MinMaxScaler()
scale_columns = ['loudness', 'tempo', 'duration_ms', 'popularity', 'key']
df[scale_columns] = scaler.fit_transform(df[scale_columns])

numeric_cols = df.select_dtypes(include=[np.number]).columns
df[numeric_cols] = df[numeric_cols].astype(np.float32)

print("5. PostgreSQL veritabanına aktarılıyor...")
try:
	engine = create_engine('postgresql://username:password@localhost:5432/music_db')
	df.to_sql('spotify_processed_data', engine, if_exists='replace', index=False, chunksize=10000)
	print("\n--- VERİTABANI MODELİ BAŞARIYLA OLUŞTURULDU ---")
	print(df['language'].value_counts().head(5))
except Exception as e:
	print(f"Veritabanı hatası: {e}")