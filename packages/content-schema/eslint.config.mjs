import { defineConfig } from 'eslint/config';
import prettier from 'eslint-config-prettier';
import { baseConfig, packageImportRules } from '../../eslint.config.mjs';

export default defineConfig([...baseConfig, ...packageImportRules(), prettier]);
