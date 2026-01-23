import { describe, it, expect } from 'vitest';
import { formatDuration, formatFileSize, formatPercentage, formatCost, } from '../../src/ui/formatters.js';
describe('Formatters', () => {
    describe('formatDuration', () => {
        it('should format seconds only', () => {
            expect(formatDuration(45)).toBe('45s');
            expect(formatDuration(5)).toBe('5s');
        });
        it('should format minutes and seconds', () => {
            expect(formatDuration(90)).toBe('1m 30s');
            expect(formatDuration(125)).toBe('2m 5s');
        });
        it('should format hours, minutes, and seconds', () => {
            expect(formatDuration(3665)).toBe('1h 1m 5s');
            expect(formatDuration(7200)).toBe('2h 0m'); // Omits 0 seconds
        });
        it('should handle zero', () => {
            expect(formatDuration(0)).toBe('0s');
        });
        it('should handle decimal seconds', () => {
            expect(formatDuration(45.8)).toBe('46s'); // Rounds to nearest second
            expect(formatDuration(90.5)).toBe('1m 31s'); // Rounds to nearest second
        });
    });
    describe('formatFileSize', () => {
        it('should format bytes', () => {
            expect(formatFileSize(500)).toBe('500 B');
            expect(formatFileSize(1023)).toBe('1023 B');
        });
        it('should format kilobytes', () => {
            expect(formatFileSize(1024)).toBe('1.0 KB');
            expect(formatFileSize(5120)).toBe('5.0 KB');
            expect(formatFileSize(1536)).toBe('1.5 KB');
        });
        it('should format megabytes', () => {
            expect(formatFileSize(1048576)).toBe('1.0 MB');
            expect(formatFileSize(5242880)).toBe('5.0 MB');
            expect(formatFileSize(1572864)).toBe('1.5 MB');
        });
        it('should format gigabytes', () => {
            expect(formatFileSize(1073741824)).toBe('1.0 GB');
            expect(formatFileSize(2147483648)).toBe('2.0 GB');
        });
        it('should handle zero', () => {
            expect(formatFileSize(0)).toBe('0 B');
        });
    });
    describe('formatPercentage', () => {
        it('should format percentage with 1 decimal', () => {
            expect(formatPercentage(0.5)).toBe('50.0%');
            expect(formatPercentage(0.333)).toBe('33.3%');
            expect(formatPercentage(0.876)).toBe('87.6%');
        });
        it('should handle 0 and 1', () => {
            expect(formatPercentage(0)).toBe('0.0%');
            expect(formatPercentage(1)).toBe('100.0%');
        });
        it('should handle very small percentages', () => {
            expect(formatPercentage(0.001)).toBe('0.1%');
            expect(formatPercentage(0.0001)).toBe('0.0%');
        });
    });
    describe('formatCost', () => {
        it('should format cost with $ symbol', () => {
            expect(formatCost(0.5)).toBe('$0.50');
            expect(formatCost(1.99)).toBe('$1.99');
            expect(formatCost(10)).toBe('$10.00');
        });
        it('should handle zero cost', () => {
            expect(formatCost(0)).toBe('$0.00');
        });
        it('should round to 2 decimals', () => {
            expect(formatCost(0.195)).toBe('$0.20');
            expect(formatCost(0.194)).toBe('$0.19');
        });
        it('should handle very small costs', () => {
            expect(formatCost(0.001)).toBe('$0.00');
            expect(formatCost(0.005)).toBe('$0.01');
        });
    });
});
//# sourceMappingURL=formatters.test.js.map