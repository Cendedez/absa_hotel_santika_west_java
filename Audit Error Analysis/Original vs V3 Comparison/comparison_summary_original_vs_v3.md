# Perbandingan Dataset Original vs V3 Audited

## Integritas Dataset

- Dataset original: `C:\Users\cencen04_\Downloads\ABSA Hotel Santika\Data Labeling\dataset_absa_labeled.csv`
- Dataset v3 audited: `C:\Users\cencen04_\Downloads\ABSA Hotel Santika\Audit Error Analysis\Step 1-3 Final Manual Review\dataset_absa_labeled_v3_final_audited.csv`
- Jumlah review original: 14,747
- Jumlah review v3: 14,747
- Jumlah kolom: 19
- Set `ID_Review` sama: Ya

## Ringkasan Perubahan

- Total sel label yang dibandingkan: 103,229 sel label (14,747 review x 7 aspek)
- Total perubahan label: 181 sel label
- Persentase perubahan label terhadap seluruh sel label: 0.1753%
- Review yang memiliki minimal satu perubahan label: 159
- Total perubahan alasan: 226
- Review yang memiliki minimal satu perubahan alasan: 176

## Perubahan Per Aspek

| aspect | label_changed_count | reason_changed_count | label_changed_pct_of_rows |
| --- | --- | --- | --- |
| Kenyamanan | 50 | 52 | 0.003391 |
| Kebersihan | 18 | 18 | 0.001221 |
| Pelayanan | 28 | 43 | 0.001899 |
| Harga | 12 | 19 | 0.000814 |
| Lokasi | 10 | 11 | 0.000678 |
| Fasilitas | 41 | 44 | 0.00278 |
| Makanan | 22 | 39 | 0.001492 |

## Perubahan Distribusi Label

| aspect | label | original_count | v3_count | delta | original_pct | v3_pct |
| --- | --- | --- | --- | --- | --- | --- |
| Fasilitas | negatif | 1505 | 1514 | 9 | 0.102055 | 0.102665 |
| Fasilitas | netral | 568 | 554 | -14 | 0.038516 | 0.037567 |
| Fasilitas | none | 11273 | 11261 | -12 | 0.764427 | 0.763613 |
| Fasilitas | positif | 1401 | 1418 | 17 | 0.095002 | 0.096155 |
| Harga | negatif | 239 | 241 | 2 | 0.016207 | 0.016342 |
| Harga | netral | 142 | 138 | -4 | 0.009629 | 0.009358 |
| Harga | none | 13757 | 13752 | -5 | 0.932868 | 0.932529 |
| Harga | positif | 609 | 616 | 7 | 0.041297 | 0.041771 |
| Kebersihan | negatif | 588 | 591 | 3 | 0.039873 | 0.040076 |
| Kebersihan | netral | 73 | 70 | -3 | 0.00495 | 0.004747 |
| Kebersihan | none | 10617 | 10606 | -11 | 0.719943 | 0.719197 |
| Kebersihan | positif | 3469 | 3480 | 11 | 0.235234 | 0.23598 |
| Kenyamanan | negatif | 1574 | 1579 | 5 | 0.106734 | 0.107073 |
| Kenyamanan | netral | 260 | 252 | -8 | 0.017631 | 0.017088 |
| Kenyamanan | none | 9028 | 9007 | -21 | 0.612192 | 0.610768 |
| Kenyamanan | positif | 3885 | 3909 | 24 | 0.263443 | 0.265071 |
| Lokasi | negatif | 257 | 258 | 1 | 0.017427 | 0.017495 |
| Lokasi | netral | 186 | 183 | -3 | 0.012613 | 0.012409 |
| Lokasi | none | 10225 | 10218 | -7 | 0.693361 | 0.692887 |
| Lokasi | positif | 4079 | 4088 | 9 | 0.276599 | 0.277209 |
| Makanan | negatif | 890 | 894 | 4 | 0.060351 | 0.060622 |
| Makanan | netral | 567 | 558 | -9 | 0.038448 | 0.037838 |
| Makanan | none | 9517 | 9515 | -2 | 0.645352 | 0.645216 |
| Makanan | positif | 3773 | 3780 | 7 | 0.255849 | 0.256323 |
| Pelayanan | negatif | 847 | 844 | -3 | 0.057435 | 0.057232 |
| Pelayanan | netral | 367 | 360 | -7 | 0.024886 | 0.024412 |
| Pelayanan | positif | 4945 | 4955 | 10 | 0.335322 | 0.336001 |

## Transisi Label Terbesar

| aspect | original_label | v3_label | count | is_changed |
| --- | --- | --- | --- | --- |
| Kenyamanan | none | positif | 27 | True |
| Fasilitas | netral | positif | 11 | True |
| Kebersihan | none | positif | 10 | True |
| Fasilitas | none | positif | 9 | True |
| Fasilitas | none | negatif | 9 | True |
| Pelayanan | none | positif | 9 | True |
| Kenyamanan | positif | none | 8 | True |
| Makanan | none | positif | 7 | True |
| Lokasi | none | positif | 6 | True |
| Kenyamanan | netral | positif | 5 | True |
| Kenyamanan | none | negatif | 5 | True |
| Makanan | netral | positif | 5 | True |
| Pelayanan | negatif | none | 5 | True |
| Pelayanan | positif | none | 5 | True |
| Pelayanan | netral | positif | 5 | True |

## Contoh Perubahan Label

| ID_Review | aspect | original_label | v3_label | Platform | Nama_Hotel | Review_Date | Text_Review | original_reason | v3_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 168 | Fasilitas | netral | positif | Agoda | Hotel Santika Bandung | 5/7/2023 | lokasi bagus bagi yang ingin menjelajahi kota bandung. lokasi sangat dekat dengan hotel aryaduta (tepat di seberang pintu keluarnya). jalan depan hotel ada 2 arah (bukan 1 arah) sehingga memudahkan kita untuk mengakses hotel. hotel santika merupakan hotel tua namun masih terawat. kamarnya luas namun semua perabotannya harus direnovasi juga fasilitasnya. sarapan memiliki pilihan terbatas namun rasanya cukup enak. area parkir mobil di basement memiliki jalur yang luas namun tempat parkir terbatas. | area parkir mobil di basement memiliki jalur yang luas namun tempat parkir terbatas | area parkir mobil di basement memiliki jalur yang luas namun tempat parkir terbatas. |
| 668 | Fasilitas | netral | negatif | Agoda | Hotel Santika Bandung | 5/26/2012 | lokasi hotel yang strategis, dilalui taksi dan angkutan kota berbagai jurusan dan dikelilingi mal, pertokoan dan "factory outlets" serta dekat dengan berbagai sekolah dan perguruan tinggi. meskipun ukuran hotel tidak luas tapi cukup nyaman. kekurangannya yaitu lobby kecil sehingga tempat duduk sedikit. juga tidak tersedia "hair dryer" di kamar meskipun sebelumnya saya baca di internet bahwa di kamar tersedia hair dryer. yang membuat saya lebih senang adalah saat itu kamar saya di-upgrade ke tipe yang lebih tinggi meskipun tidak diminta. | kekurangannya yaitu lobby kecil sehingga tempat duduk sedikit. | kekurangannya yaitu lobby kecil sehingga tempat duduk sedikit. |
| 697 | Fasilitas | negatif | none | Agoda | Hotel Santika Bogor | 1/10/2025 | lokasinya bagus karena bersebelahan dengan pusat perbelanjaan sehingga tidak perlu jauh-jauh. namun secara keseluruhan fasilitas terasa agak tua, mungkin karena hotelnya sudah tua. stafnya ramah, saya suka lokasinya, dan harganya. juga, ada pembangunan yang sedang berlangsung di sebelah, jadi saya tidur siang, tapi selain kebisingan, saya tidak punya keluhan. | secara keseluruhan fasilitas terasa agak tua |  |
| 1064 | Fasilitas | none | negatif | Agoda | Hotel Santika Bogor | 11/5/2014 | satu malam menginap layanan grup tidak baik! harus menyelesaikannya sebelum kedatangan kamar jika belum siap. kapasitas liftnya tidak baik |  | kapasitas liftnya tidak baik |
| 1115 | Fasilitas | netral | positif | Agoda | Hotel Santika Bogor | 10/10/2013 | saya pernah menginap di grup hotel santika di indonesia, seperti malang dan balikpapang. sama seperti hotel lainnya, staf santika bogor terlatih dan ramah. kamarnya sederhana tapi baik untuk menginap. wi-fi berkecepatan tinggi dan cukup stabil. hotel terletak tepat di sebelah pusat perbelanjaan anda bisa mendapatkan semuanya di sana. | wi-fi berkecepatan tinggi dan cukup stabil. | wi-fi berkecepatan tinggi dan cukup stabil. |
| 1136 | Fasilitas | positif | negatif | Agoda | Hotel Santika Bogor | 2/16/2013 | karena hujan selalu turun di sore hari, kami dapat, di waktu senggang, berbelanja atau makan malam tanpa basah kuyup atau harus mencari taksi dengan panik. sarapannya memuaskan. ruangan itu baik-baik saja hanya saja transmisi televisi sering terputus dan beberapa saluran meskipun ditunjukkan dalam daftar tidak ada | saja hanya saja transmisi televisi sering terputus dan beberapa saluran meskipun | ruangan itu baik-baik saja hanya saja transmisi televisi sering terputus dan beberapa saluran meskipun ditunjukkan dalam daftar tidak ada |
| 1385 | Fasilitas | netral | positif | Agoda | Hotel Santika Bogor | 4/12/2024 | hotel bersih dan nyaman, overall baik banget, hanya parkir kendaraan yang kurang baik karena kalau keluar cari2 petugasnya dulu | overall baik banget, hanya parkir kendaraan yang kurang baik karena kalau keluar | hotel bersih dan nyaman, overall baik banget, hanya parkir kendaraan yang kurang baik karena kalau keluar cari2 petugasnya dulu |
| 1635 | Fasilitas | netral | negatif | Agoda | Hotel Santika Bogor | 8/26/2012 | terletak di lokasi yang strategis untuk perjalanan dari jakarta, dengan lokasi yang berdampingan dengan botani square menambah kenyamanan dalam liburan. tetapi, fasilitas amenities di kamar mandi sangat minim. cocok untuk tempat menginap keluarga yang melakukan perjalanan ke bogor hanya untuk sekedar jalan2. | tetapi, fasilitas amenities di kamar mandi sangat minim. | tetapi, fasilitas amenities di kamar mandi sangat minim. |
| 1834 | Fasilitas | positif | none | Agoda | Hotel Santika Cirebon | 2/7/2024 | menginap semalam, kamarnya sangat bersih, stafnya cepat tanggap dan sangat ramah. fasilitasnya lengkap dan anda juga bisa meminta fasilitas lain seperti pengering rambut dan staf akan mengirimkannya ke kamar anda. sarapannya enak tapi tidak ada yang luar biasa tentang sarapan. tampilan hotelnya mungkin agak tua tapi secara keseluruhan sepadan dengan harganya. | fasilitasnya lengkap dan anda juga bisa meminta fasilitas |  |
| 2287 | Fasilitas | netral | positif | Agoda | Hotel Santika Cirebon | 1/5/2015 | sangat menyenangkan dan terjaga privacy, sehingga kami dapat dengan leluasa menikmati fasilitas hotel yang disediakan. | dapat dengan leluasa menikmati fasilitas hotel yang disediakan | sangat menyenangkan dan terjaga privacy, sehingga kami dapat dengan leluasa menikmati fasilitas hotel yang disediakan. |
| 2366 | Fasilitas | netral | positif | Agoda | Hotel Santika Cirebon | 3/16/2012 | hotel nya bersih dan nyaman serta kolam renang besar dan bersih dan kamar nya besar dan harga nya terjangkau | hotel nya bersih dan nyaman serta kolam renang besar dan bersih dan kamar nya besar dan harga | hotel nya bersih dan nyaman serta kolam renang besar dan bersih dan kamar nya besar dan harga nya terjangkau |
| 2413 | Fasilitas | none | negatif | Agoda | Hotel Santika Depok | 3/23/2025 | nyaman, strategis di mall, menawarkan sahur, dan staf ramah, kamar bersih, sayangnya tidak ada kulkas mini. |  | nyaman, strategis di mall, menawarkan sahur, dan staf ramah, kamar bersih, sayangnya tidak ada kulkas mini. |
| 2834 | Fasilitas | none | negatif | Agoda | Hotel Santika Depok | 1/19/2022 | floordrain tidak berfungsi. jadi saya harus buka floordrainnya biar airnya tidak menggenang. saya bermalam di unit yang exclusive. hanya dapat buah 3 pcs. penerangan kurang. karpet di ruang family kotor banget sama sofa belum pernah di dryclean kayaknya. selain hal ini nyaman. |  | floordrain tidak berfungsi. |
| 2860 | Fasilitas | netral | negatif | Agoda | Hotel Santika Depok | 3/22/2017 | lokasi di mall dengan banyak pilihan restoran bahkan departemen store. air minum yang disediakan lebih banyak dari standar hotel lain, yaitu 4 botol dengan ukuran sedang. kenyamanan tidur sangat memuaskan dengan bed yang sangat nyaman dan 2 bantal yang nyaman di masing masing bed (twin). kondisi kamar sangat bersih dan fasilitas kamar mandi juga lengkap. yang cukup mengganggu adalah suhu air shower yang sangat tidak stabil, panas dingin bergantian. namun yang paling mengecewakan untuk kami adalah fasilitas wi-fi yang amat sangat lambat, bahkan tidak bisa kami gunakan sama sekali. | fasilitas kamar mandi juga lengkap. fasilitas wi-fi yang amat sangat lambat | namun yang paling mengecewakan untuk kami adalah fasilitas wi-fi yang amat sangat lambat, bahkan tidak bisa kami gunakan sama sekali. |
| 3852 | Fasilitas | netral | positif | Tiket | Hotel Santika Bandung | 6/14/2019 | yang saya sukai: - fasilitas nya baik - makanan nya baik - karyawan nya ramah2 - tempatnya strategis saran: - tempat parkiran mobilnya tolong di perluas lagi. | fasilitas nya baik / tempat parkiran mobilnya tolong di perluas lagi | yang saya sukai: - fasilitas nya baik - makanan nya baik - karyawan nya ramah2 - tempatnya strategis saran: - tempat parkiran mobilnya tolong di perluas lagi. |
| 4135 | Fasilitas | none | negatif | Tiket | Hotel Santika Bandung | 9/8/2021 | hotelnya sudah tua, gatau karna penuh atau gimana dapet kamar yang sudah lama tidak dipake kayanya sampe water heaternya harus minta dinyalain dulu ke teknisinya, dan bau lembab banget, sarapan buat sekelas santika kurang banget |  | hotelnya sudah tua, gatau karna penuh atau gimana dapet kamar yang sudah lama tidak dipake kayanya sampe water heaternya harus minta dinyalain dulu ke teknisinya, dan bau lembab banget, sarapan buat sekelas santika kurang banget |
| 4486 | Fasilitas | netral | positif | Tiket | Hotel Santika Mega City Bekasi | 7/8/2024 | akses mudah ke tempat-tempat terkenal. parkir nyaman. suasana kolam tenang. | parkir nyaman. | parkir nyaman. |
| 4782 | Fasilitas | netral | positif | Tiket | Hotel Santika Mega City Bekasi | 1/13/2019 | pengalaman yang memuaskan, kamar agak sempit sii hehehe, cuma bersih banget dan untuk saluran televisi nya banyak semutnya, tapi hampir semua baik sii, dari pelayanan receptions nya yang ramah tamah. okonya bagus | bersih banget dan untuk saluran televisi nya banyak semutnya, tapi hampir semua baik sii | pengalaman yang memuaskan, kamar agak sempit sii hehehe, cuma bersih banget dan untuk saluran televisi nya banyak semutnya, tapi hampir semua baik sii, dari pelayanan receptions nya yang ramah tamah. |
| 5539 | Fasilitas | netral | positif | Tiket | Hotel Santika Cirebon | 9/9/2024 | kebersihan terjaga maksimal. kolam renang dengan pemandangan indah. kolam renang dengan pemandangan indah. | kolam renang dengan pemandangan indah. | kolam renang dengan pemandangan indah. |
| 5719 | Fasilitas | none | negatif | Tiket | Hotel Santika Cirebon | 4/21/2019 | lokasi strstegis, makan pagi baik, cuma air panas kurang dan shower kurang kencang. |  | lokasi strstegis, makan pagi baik, cuma air panas kurang dan shower kurang kencang. |

## Interpretasi Singkat

- Dataset v3 tidak mengubah struktur data, jumlah review, atau ID review.
- Perubahan v3 bersifat targeted correction dari hasil audit error analysis, bukan relabeling total.
- Kelas `netral` berkurang pada semua aspek karena guideline final memperketat penggunaan `netral`; kelas ini hanya dipakai ketika aspek disebut secara deskriptif tanpa evaluasi jelas.
- Beberapa label `none` berubah menjadi `positif` atau `negatif` ketika review sebenarnya memuat aspek dan sentimen yang jelas.
- Beberapa label sentimen berubah menjadi `none` ketika alasan/aspek tidak cukup kuat atau alasan berada di aspek yang salah.
