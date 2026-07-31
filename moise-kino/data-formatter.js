class DataFormatter {
    static formatCurrency(cents) {
        const value = (Number(cents) || 0) / 100;
        return value.toLocaleString('de-DE', { style: 'currency', currency: 'EUR' });
    }
}
