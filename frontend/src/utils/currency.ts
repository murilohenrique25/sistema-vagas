const brlFormatter = new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
});

export function formatBRL(value: number | string | null | undefined): string {
    const amount = Number(value ?? 0);
    return brlFormatter.format(Number.isFinite(amount) ? amount : 0);
}
