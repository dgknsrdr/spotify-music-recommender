from flask import Flask, render_template, request
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sklearn.metrics.pairwise import cosine_similarity
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

app = Flask(__name__)

# SPOTIFY DASHBOARD KODLARINI KONTROL ET
client_id = 'YOUR_SPOTIFY_CLIENT_ID'
client_secret = 'YOUR_SPOTIFY_CLIENT_SECRET'

sp = spotipy.Spotify(
	auth_manager=SpotifyClientCredentials(
		client_id=client_id,
		client_secret=client_secret,
		cache_handler=None
	)
)

engine = create_engine('postgresql://username:password@localhost:5432/music_db')

feature_cols = [
	'popularity', 'duration_ms', 'explicit', 'danceability', 'energy',
	'key', 'loudness', 'mode', 'speechiness', 'acousticness',
	'instrumentalness', 'liveness', 'valence', 'tempo'
]


def get_spotify_info_by_id(spotify_id):
	try:
		track = sp.track(spotify_id)
		if track:
			img_url = track['album']['images'][0]['url'] if track['album'][
				'images'] else "https://via.placeholder.com/300"
			preview = track.get('preview_url')
			spotify_link = track['external_urls']['spotify']
			return img_url, preview, spotify_link
	except Exception as e:
		print(f"Spotify API Hatası: {e}")
	return "https://via.placeholder.com/300", None, "#"


@app.route('/', methods=['GET', 'POST'])
def index():
	recommendations = []
	grouped_artists = {}
	search_query = ""
	error_msg = ""
	search_mode = "song"

	if request.method == 'POST':
		search_query = request.form.get('song_name').strip()
		search_mode = request.form.get('search_mode', 'song')

		# --- GÜVENLİK DUVARI 1: Kısa aramaları engelle ---
		if len(search_query) < 3:
			error_msg = "Arama yapabilmek için lütfen en az 3 karakter giriniz."
			return render_template('index.html', recs=recommendations, artists_data=grouped_artists, query=search_query,
								   error=error_msg, mode=search_mode)

		# --- MOD 1: DOĞRUDAN SANATÇI ARAMASI---
		if search_mode == 'artist':
			query_artist = f"SELECT * FROM spotify_processed_data WHERE LOWER(artists) LIKE '%%{search_query.lower()}%%' ORDER BY popularity DESC;"
			artist_songs_df = pd.read_sql(query_artist, engine)

			if not artist_songs_df.empty:

				# 1. ADIM: Benzersiz sanatçıları tespit et
				artist_max_pop = {}
				for idx, row in artist_songs_df.iterrows():
					raw_artists = str(row['artists']).replace("[", "").replace("]", "").replace("'", "").split(",")
					for single_artist in raw_artists:
						clean_name = single_artist.strip()
						if search_query.lower() in clean_name.lower():
							artist_max_pop[clean_name] = max(artist_max_pop.get(clean_name, 0), row['popularity'])

				# 2. ADIM: Akıllı sıralama ve ilk 5 sanatçıyı seçme
				def get_artist_sorting_score(artist_item):
					name = artist_item[0].lower()
					pop = artist_item[1]
					q = search_query.lower()
					if name == q:
						return (0, -pop)
					elif name.startswith(q):
						return (1, -pop)
					else:
						return (2, -pop)

				sorted_artists = sorted(artist_max_pop.items(), key=get_artist_sorting_score)
				top_5_artists = [artist_name for artist_name, _ in sorted_artists[:5]]


				# Spotify'da bu 5 sanatçıyı aratıp resimlerini TEK BİR İSTEKTE topluca alıyoruz.

				artist_images = {}
				for artist_name in top_5_artists:
					try:
						# Sanatçıyı Spotify'da hızlıca aratıp profil resmini alıyoruz
						search_result = sp.search(q=f"artist:{artist_name}", type="artist", limit=1)
						if search_result and search_result['artists']['items']:
							images = search_result['artists']['items'][0]['images']
							artist_images[artist_name] = images[0][
								'url'] if images else "https://via.placeholder.com/300"
						else:
							artist_images[artist_name] = "https://via.placeholder.com/300"
					except:
						artist_images[artist_name] = "https://via.placeholder.com/300"

				# 3. ADIM: Seçilen ilk 5 sanatçının şarkılarını veritabanından çek (API'ye sormadan!)
				total_song_count = 0
				for current_artist in top_5_artists:
					if total_song_count >= 200:  # Toplamda maksimum 200 şarkı
						break

					if current_artist not in grouped_artists:
						grouped_artists[current_artist] = []

					# Sanatçının profil resmini yukarıda tek seferde çözmüştük, onu alıyoruz
					chosen_img = artist_images.get(current_artist, "https://via.placeholder.com/300")

					for idx, row in artist_songs_df.iterrows():
						if total_song_count >= 100:
							break
						raw_artists_list = str(row['artists']).replace("[", "").replace("]", "").replace("'", "").split(
							",")
						cleaned_list = [name.strip() for name in raw_artists_list]

						if current_artist in cleaned_list:
							#Şarkı detayları için API'ye gitmiyoruz!
							# Resmi direkt sanatçının kendi resmi yapıyoruz. Bu sayfa yüklenme süresini 0 saniyeye indirir!
							grouped_artists[current_artist].append({
								'name': row['name'],
								'artist': str(row['artists']).replace("[", "").replace("]", "").replace("'", ""),
								'image': chosen_img,  # API'den gelen tekil resim
								'preview': None,  # Hız için önizlemeyi kapattık
								'spotify_link': f"https://open.spotify.com/track/{row['id']}"
								# ID'den linki otomatik üretiyoruz
							})
							total_song_count += 1
			else:
				error_msg = f"'{search_query}' kriterini içeren bir sanatçı veritabanında bulunamadı."

		# --- MOD 2: ŞARKIYA GÖRE ÖNERİ MOTORU ---
		else:
			if "-" in search_query:
				parts = search_query.split("-")
				song_part = parts[0].strip().lower()
				artist_part = parts[1].strip().lower()
				query_find = f"SELECT * FROM spotify_processed_data WHERE LOWER(TRIM(name)) = '{song_part}' AND LOWER(artists) LIKE '%%{artist_part}%%' LIMIT 1;"
			else:
				query_find = f"SELECT * FROM spotify_processed_data WHERE LOWER(TRIM(name)) = '{search_query.lower()}' ORDER BY popularity DESC LIMIT 1;"

			target_df = pd.read_sql(query_find, engine)

			if not target_df.empty:
				try:
					target_song = target_df.iloc[0]
					target_lang = target_song['language']
					target_pop = target_song['popularity']

					raw_artist = str(target_song['artists']).replace("[", "").replace("]", "").replace("'", "")
					target_main_artist = raw_artist.split(",")[0].strip().lower()

					if target_pop > 1:
						min_pop = max(0, target_pop - 20)
					else:
						min_pop = max(0.0, target_pop - 0.20)

					query_pool = f"SELECT * FROM spotify_processed_data WHERE language = '{target_lang}' AND popularity >= {min_pop};"
					pool_df = pd.read_sql(query_pool, engine)
					pool_df.reset_index(drop=True, inplace=True)

					if len(pool_df) < 10:
						ek_esneklik = 15 if target_pop > 1 else 0.15
						query_pool = f"SELECT * FROM spotify_processed_data WHERE language = '{target_lang}' AND popularity >= {max(0, target_pop - (10 + ek_esneklik))};"
						pool_df = pd.read_sql(query_pool, engine)
						pool_df.reset_index(drop=True, inplace=True)

					if target_song['id'] not in pool_df['id'].values:
						pool_df = pd.concat([target_df, pool_df], ignore_index=True)
						pool_df.reset_index(drop=True, inplace=True)

					song_idx = pool_df[pool_df['id'] == target_song['id']].index[0]

					pool_features = pool_df[feature_cols].to_numpy()
					vector = pool_features[song_idx].reshape(1, -1)

					scores = cosine_similarity(vector, pool_features)
					all_indices = scores[0].argsort()[::-1]

					artist_matches = []
					other_matches = []

					for i in all_indices:
						if i == song_idx:
							continue
						curr_artist_raw = str(pool_df.iloc[i]['artists']).replace("[", "").replace("]", "").replace("'",
																													"")
						curr_main_artist = curr_artist_raw.split(",")[0].strip().lower()
						match_data = {'name': pool_df.iloc[i]['name'], 'artist': curr_artist_raw,
									  'id': pool_df.iloc[i]['id']}
						if target_main_artist in curr_main_artist or curr_main_artist in target_main_artist:
							artist_matches.append(match_data)
						else:
							other_matches.append(match_data)

					final_queue = artist_matches[:2] + other_matches[:3]

					for item in final_queue:
						img_url, preview, spotify_link = get_spotify_info_by_id(item['id'])
						recommendations.append({
							'name': item['name'],
							'artist': item['artist'],
							'image': img_url,
							'preview': preview,
							'spotify_link': spotify_link
						})
				except Exception as e:
					print(f"Algoritma Hatası: {e}")
					error_msg = "Hesaplama motorunda bir sorun oluştu."
			else:
				error_msg = f"'{search_query}' kriterlerine uygun şarkı veritabanında bulunamadı."

	return render_template('index.html', recs=recommendations, artists_data=grouped_artists, query=search_query,
						   error=error_msg, mode=search_mode)


if __name__ == '__main__':
	app.run(debug=True)