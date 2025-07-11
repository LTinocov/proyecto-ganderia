PRAGMA foreign_keys = OFF;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;

BEGIN TRANSACTION;

-- Tabla de usuarios
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    tipo TEXT NOT NULL CHECK(tipo IN ('administrador', 'trabajador')),
    codigo TEXT NOT NULL UNIQUE
);

-- Tabla de reportes diarios
CREATE TABLE IF NOT EXISTS reportes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo_usuario TEXT NOT NULL,
    codigo_ganado TEXT NOT NULL,
    fecha TEXT NOT NULL,
    hora TEXT NOT NULL,
    semana TEXT NOT NULL,
    UNIQUE(codigo_ganado, semana),
    FOREIGN KEY(codigo_usuario) REFERENCES usuarios(codigo)
);

-- Tabla de reportes semanales
CREATE TABLE IF NOT EXISTS reportes_semanales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo_usuario TEXT NOT NULL,
    codigo_ganado TEXT NOT NULL,
    fecha TEXT NOT NULL,
    hora TEXT NOT NULL,
    semana TEXT NOT NULL,
    FOREIGN KEY(codigo_usuario) REFERENCES usuarios(codigo)
);

-- Insertar usuarios iniciales
INSERT OR IGNORE INTO usuarios (nombre, tipo, codigo) VALUES
('Alexandra Tenorio', 'administrador', '1955'),
('Luis Tinoco', 'administrador', '8863'),
('Jose Tenorio', 'administrador', '7632'),
('Ivannia Obando', 'administrador', '4481'),
('Don Cecil Alfaro', 'administrador', '1174'),
('Raul Aguilar', 'trabajador', '2014'),
('Josue Aguilar', 'trabajador', '5498'),
('Oscar Aguilar', 'trabajador', '3240'),
('Armando Cerdas', 'trabajador', '9549'),
('Cesar González', 'trabajador', '2218'),
('Tayra Jimenez', 'trabajador', '0251'),
('Cristopher Mora', 'trabajador', '3300'),
('Carlos Obando', 'trabajador', '4832'),
('Luis Obando', 'trabajador', '5190'),
('Andres Perez', 'trabajador', '9383'),
('Daniel Perez', 'trabajador', '7224'),
('Adrian Rojas', 'trabajador', '8782'),
('Jose Serrano', 'trabajador', '9010'),
('Francisco Solano', 'trabajador', '1314'),
('Aaron Solano', 'trabajador', '1010');

-- Índices para optimización
CREATE INDEX IF NOT EXISTS idx_usuarios_codigo ON usuarios(codigo);
CREATE INDEX IF NOT EXISTS idx_reportes_semana ON reportes(semana);
CREATE INDEX IF NOT EXISTS idx_reportes_semanales_semana ON reportes_semanales(semana);

COMMIT;

PRAGMA foreign_keys = ON;
PRAGMA optimize;