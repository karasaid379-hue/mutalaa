// The package ships no type declarations. Only lib/turkish-stemmer.js is imported (index.js
// loads fs and path and opens the algorithm file with a dynamic require; K-44 item 1).
declare module 'snowball-stemmers-js/lib/turkish-stemmer.js' {
  export default class TurkishStemmer {
    constructor();
    stemWord(word: string): string;
  }
}
