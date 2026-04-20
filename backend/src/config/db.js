// betgenius-backend/src/config/db.js
const { Pool } = require('pg');
require('dotenv').config();

// FIX S-TIER: Força o uso estrito do POSTGRES_URL conforme diretriz do Arquiteto
const connectionString = process.env.POSTGRES_URL;

if (!connectionString) {
    console.error("❌ [FATAL] POSTGRES_URL não declarada no arquivo .env");
    process.exit(1);
}

const pool = new Pool({
    connectionString,
    ssl: { rejectUnauthorized: false } // Necessário para conexões seguras no Neon
});

pool.on('error', (err, client) => {
    console.error('❌ Erro inesperado no pool do Postgres', err);
});

module.exports = pool;