#include <stdio.h>

int main(void)
{
    int pilihan;
    double angka_1, angka_2, hasil;

    printf("KALKULATOR SEDERHANA\n");
    printf("====================\n");
    printf("1. Penjumlahan\n");
    printf("2. Pengurangan\n");
    printf("3. Perkalian\n");
    printf("4. Pembagian\n");
    printf("Masukkan pilihan: ");
    scanf("%d", &pilihan);
    printf("Masukkan angka pertama: ");
    scanf("%lf", &angka_1);
    printf("Masukkan angka kedua: ");
    scanf("%lf", &angka_2);

    switch (pilihan)
    {
    case 1:
        hasil = angka_1 + angka_2;
        printf("Hasil: %.2f\n", hasil);
        break;
    case 2:
        hasil = angka_1 - angka_2;
        printf("Hasil: %.2f\n", hasil);
        break;
    case 3:
        hasil = angka_1 * angka_2;
        printf("Hasil: %.2f\n", hasil);
        break;
    case 4:
        if (angka_2 != 0.0)
        {
            hasil = angka_1 / angka_2;
            printf("Hasil: %.2f\n", hasil);
        }
        else
        {
            printf("Pembagian dengan nol tidak diperbolehkan.\n");
        }
        break;
    default:
        printf("Pilihan tidak tersedia.\n");
        break;
    }

    return 0;
}
