/**
 * Bulk selection of the link candidates queue. It is closed (K-48, karar 5): the API does not give the
 * candidate class (tutarsız, toplu, gri bölge) yet, so a bulk approval could not be sampled by class. A18 adds
 * the class to the API and flips this flag; the sample flow (10 percent, one "Hatalı" cancels) is already built
 * and tested with the flag injected.
 */
export const BULK_ENABLED = false;
