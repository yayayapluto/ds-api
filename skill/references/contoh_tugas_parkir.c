/*
Nama        : -
NIM         : -
Kelas       : -
Modul       : 4
Deskripsi   : Program menghitung tarif parkir berdasarkan
              jenis kendaraan, durasi, dan status member.
*/

#include <stdio.h>

int main(void)
{
    const double DISKON_MEMBER = 0.10;
    int pilihan, durasi, status;
    double tarif_jam_pertama = 0.0, tarif_per_jam = 0.0, tarif_maksimal = 0.0;
    double tarif_awal = 0.0, diskon = 0.0, total_bayar = 0.0;

    printf("================================================\n");
    printf("PROGRAM TARIF PARKIR\n");
    printf("================================================\n");
    printf("Jenis kendaraan:\n");
    printf("1. Sepeda motor\n");
    printf("2. Mobil\n");
    printf("3. Bus\n");
    printf("Masukkan pilihan : ");
    scanf("%d", &pilihan);
    printf("Masukkan durasi parkir : ");
    scanf("%d", &durasi);
    printf("Status member:\n");
    printf("0. Bukan member\n");
    printf("1. Member\n");
    printf("Masukkan status : ");
    scanf("%d", &status);

    switch (pilihan)
    {
    case 1:
        tarif_jam_pertama = 3000.0;
        tarif_per_jam = 1500.0;
        tarif_maksimal = 15000.0;
        break;
    case 2:
        tarif_jam_pertama = 5000.0;
        tarif_per_jam = 3000.0;
        tarif_maksimal = 30000.0;
        break;
    case 3:
        tarif_jam_pertama = 10000.0;
        tarif_per_jam = 5000.0;
        tarif_maksimal = 60000.0;
        break;
    default:
        printf("Jenis kendaraan tidak valid.\n");
        return 1;
    }

    if (durasi < 1)
    {
        printf("Durasi tidak valid.\n");
        return 1;
    }

    if ((status != 0) && (status != 1))
    {
        printf("Status member tidak valid.\n");
        return 1;
    }

    if (durasi == 1)
    {
        tarif_awal = tarif_jam_pertama;
    }
    else
    {
        tarif_awal = tarif_jam_pertama + (double)(durasi - 1) * tarif_per_jam;
    }

    if (tarif_awal > tarif_maksimal)
    {
        tarif_awal = tarif_maksimal;
    }

    if ((status == 1) && (durasi >= 2))
    {
        diskon = tarif_awal * DISKON_MEMBER;
    }

    total_bayar = tarif_awal - diskon;

    printf("RINCIAN PARKIR\n");
    printf("------------------------------------------------\n");
    if (pilihan == 1)
    {
        printf("Jenis kendaraan : Sepeda motor\n");
    }
    else if (pilihan == 2)
    {
        printf("Jenis kendaraan : Mobil\n");
    }
    else
    {
        printf("Jenis kendaraan : Bus\n");
    }
    printf("Durasi : %d jam\n", durasi);
    printf("Tarif awal : Rp%.2f\n", tarif_awal);
    printf("Diskon member : Rp%.2f\n", diskon);
    printf("Total bayar : Rp%.2f\n", total_bayar);
    printf("================================================\n");

    return 0;
}