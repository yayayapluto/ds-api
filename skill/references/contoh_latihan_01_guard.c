#include <stdio.h>

int main(void)
{
    double nilai;

    printf("Masukkan nilai akhir: ");
    scanf("%lf", &nilai);

    if ((nilai < 0.0) || (nilai > 100.0))
    {
        printf("Nilai tidak valid.\n");
    }
    else if (nilai >= 60.0)
    {
        printf("Status: Lulus\n");
    }
    else
    {
        printf("Status: Belum lulus\n");
    }

    return 0;
}