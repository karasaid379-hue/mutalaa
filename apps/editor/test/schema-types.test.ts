import { describe, expectTypeOf, it } from 'vitest';
import type { components } from '@/api/schema';

type ReviewItem = components['schemas']['ReviewItemDto'];

// Tip testi: sözleşme düzeltmesi (A15.0a) üretilmiş tiplere yansımalı.
describe('üretilmiş API tipleri', () => {
  it('sayısal alanlar yalnız number olur (Strict sayı kuralı)', () => {
    expectTypeOf<ReviewItem['id']>().toEqualTypeOf<number>();
  });

  it('liste öğesi onceki, onerilen ve duzenlenen alanlarını taşır', () => {
    expectTypeOf<ReviewItem>().toHaveProperty('onceki');
    expectTypeOf<ReviewItem>().toHaveProperty('onerilen');
    expectTypeOf<ReviewItem>().toHaveProperty('duzenlenen');
  });
});
