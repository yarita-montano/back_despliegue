-- ============================================================
-- PLATAFORMA INTELIGENTE DE ATENCIÓN DE EMERGENCIAS VEHICULARES
-- Base de Datos - PostgreSQL (para FastAPI)
-- ============================================================

-- Para crear la base de datos, ejecutar desde psql:
-- CREATE DATABASE emergencias_vehiculares;
-- \c emergencias_vehiculares

-- ==========================================
-- 1. CATÁLOGOS (Diccionarios)
-- ==========================================

CREATE TABLE estado_incidente (
    id_estado       SERIAL PRIMARY KEY,
    nombre          VARCHAR(50)  NOT NULL,   -- pendiente | en_proceso | atendido | cancelado
    descripcion     VARCHAR(200)
);

CREATE TABLE categoria_problema (
    id_categoria    SERIAL PRIMARY KEY,
    nombre          VARCHAR(50)  NOT NULL,   -- bateria | llanta | choque | motor | llaves | otros | incierto
    descripcion     VARCHAR(200),
    icono_url       VARCHAR(255)             -- ícono para la app móvil
);

CREATE TABLE prioridad (
    id_prioridad    SERIAL PRIMARY KEY,
    nivel           VARCHAR(50)  NOT NULL,   -- baja | media | alta | critica
    orden           INT          NOT NULL    -- 1=baja ... 4=critica
);

CREATE TABLE estado_asignacion (
    id_estado_asignacion SERIAL PRIMARY KEY,
    nombre          VARCHAR(50)  NOT NULL    -- pendiente | aceptada | rechazada | en_camino | completada
);

CREATE TABLE tipo_evidencia (
    id_tipo_evidencia SERIAL PRIMARY KEY,
    nombre          VARCHAR(50)  NOT NULL    -- imagen | audio | texto
);

CREATE TABLE rol (
    id_rol          SERIAL PRIMARY KEY,
    nombre          VARCHAR(50)  NOT NULL    -- cliente | taller | tecnico | admin
);

CREATE TABLE metodo_pago (
    id_metodo_pago  SERIAL PRIMARY KEY,
    nombre          VARCHAR(50)  NOT NULL    -- tarjeta | transferencia | efectivo | qr
);

CREATE TABLE estado_pago (
    id_estado_pago  SERIAL PRIMARY KEY,
    nombre          VARCHAR(50)  NOT NULL    -- pendiente | procesando | completado | fallido | reembolsado
);


-- ==========================================
-- 2. ENTIDADES PRINCIPALES
-- ==========================================

-- 2.1 USUARIO (clientes de la app móvil y admins)
CREATE TABLE usuario (
    id_usuario      SERIAL PRIMARY KEY,
    id_rol          INT          NOT NULL,
    nombre          VARCHAR(100) NOT NULL,
    email           VARCHAR(100) NOT NULL UNIQUE,
    telefono        VARCHAR(20),
    password_hash   VARCHAR(255) NOT NULL,              -- contraseña hasheada (bcrypt)
    push_token      VARCHAR(255),                       -- token FCM/APNs para notificaciones push
    activo          BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP    NOT NULL DEFAULT NOW(),
    FOREIGN KEY (id_rol) REFERENCES rol(id_rol)
);

-- 2.2 VEHÍCULO
CREATE TABLE vehiculo (
    id_vehiculo     SERIAL PRIMARY KEY,
    id_usuario      INT          NOT NULL,
    placa           VARCHAR(20)  NOT NULL,
    marca           VARCHAR(50),
    modelo          VARCHAR(50),
    anio            INT,                                -- año del vehículo (ayuda a la IA)
    color           VARCHAR(30),                        -- color (ayuda a la IA a identificarlo en fotos)
    activo          BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP    NOT NULL DEFAULT NOW(),
    FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario)
);

-- 2.3 TALLER
CREATE TABLE taller (
    id_taller       SERIAL PRIMARY KEY,
    nombre          VARCHAR(100) NOT NULL,
    email           VARCHAR(100) NOT NULL UNIQUE,
    telefono        VARCHAR(20),
    password_hash   VARCHAR(255) NOT NULL,              -- los talleres también se autentican
    push_token      VARCHAR(255),                       -- para notificaciones push al taller
    latitud         DOUBLE PRECISION,
    longitud        DOUBLE PRECISION,
    direccion       VARCHAR(255),
    capacidad_max   INT          NOT NULL DEFAULT 5,    -- máx incidentes simultáneos
    activo          BOOLEAN      NOT NULL DEFAULT TRUE,
    verificado      BOOLEAN      NOT NULL DEFAULT FALSE,-- admin valida al taller antes de operar
    disponible      BOOLEAN      NOT NULL DEFAULT TRUE, -- toggle operativo (pausa/reanuda) para CU-17
    created_at      TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP    NOT NULL DEFAULT NOW()
);

-- 2.4 SERVICIOS QUE OFRECE CADA TALLER (para el motor de asignación)
CREATE TABLE taller_servicio (
    id_taller_servicio SERIAL PRIMARY KEY,
    id_taller       INT          NOT NULL,
    id_categoria    INT          NOT NULL,              -- qué tipo de problema atiende
    servicio_movil  BOOLEAN      NOT NULL DEFAULT FALSE,-- ¿puede ir al lugar del incidente?
    FOREIGN KEY (id_taller)    REFERENCES taller(id_taller),
    FOREIGN KEY (id_categoria) REFERENCES categoria_problema(id_categoria),
    CONSTRAINT uq_taller_categoria UNIQUE (id_taller, id_categoria)
);

-- 2.5 TÉCNICO
CREATE TABLE tecnico (
    id_tecnico      SERIAL PRIMARY KEY,
    id_taller       INT          NOT NULL,
    nombre          VARCHAR(100) NOT NULL,
    telefono        VARCHAR(20),
    disponible      BOOLEAN      NOT NULL DEFAULT TRUE,
    latitud         DOUBLE PRECISION,                   -- ubicación actual del técnico
    longitud        DOUBLE PRECISION,
    activo          BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP    NOT NULL DEFAULT NOW(),
    FOREIGN KEY (id_taller) REFERENCES taller(id_taller)
);


-- ==========================================
-- 3. NÚCLEO TRANSACCIONAL
-- ==========================================

-- 3.1 INCIDENTE
CREATE TABLE incidente (
    id_incidente        SERIAL PRIMARY KEY,
    id_usuario          INT          NOT NULL,
    id_vehiculo         INT          NOT NULL,
    id_estado           INT          NOT NULL,
    id_categoria        INT,                            -- clasificado por IA
    id_prioridad        INT,                            -- prioridad asignada por IA
    latitud             DOUBLE PRECISION NOT NULL,
    longitud            DOUBLE PRECISION NOT NULL,
    descripcion_usuario TEXT,                           -- texto libre del usuario (opcional)
    resumen_ia          TEXT,                           -- ficha estructurada generada por IA
    clasificacion_ia_confianza DOUBLE PRECISION,        -- % de confianza (0.0 - 1.0)
    requiere_revision_manual BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP    NOT NULL DEFAULT NOW(),
    FOREIGN KEY (id_usuario)   REFERENCES usuario(id_usuario),
    FOREIGN KEY (id_vehiculo)  REFERENCES vehiculo(id_vehiculo),
    FOREIGN KEY (id_estado)    REFERENCES estado_incidente(id_estado),
    FOREIGN KEY (id_categoria) REFERENCES categoria_problema(id_categoria),
    FOREIGN KEY (id_prioridad) REFERENCES prioridad(id_prioridad)
);


-- ==========================================
-- 4. TABLAS INTERMEDIAS Y TRAZABILIDAD
-- ==========================================

-- 4.1 ASIGNACIÓN (incidente → taller → técnico)
CREATE TABLE asignacion (
    id_asignacion       SERIAL PRIMARY KEY,
    id_incidente        INT          NOT NULL,
    id_taller           INT          NOT NULL,
    id_tecnico          INT,                            -- puede asignarse después
    id_estado_asignacion INT         NOT NULL,
    eta_minutos         INT,                            -- tiempo estimado de llegada
    costo_estimado      DECIMAL(10,2),
    nota_taller         TEXT,                           -- observaciones del taller
    created_at          TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP    NOT NULL DEFAULT NOW(),
    FOREIGN KEY (id_incidente)         REFERENCES incidente(id_incidente),
    FOREIGN KEY (id_taller)            REFERENCES taller(id_taller),
    FOREIGN KEY (id_tecnico)           REFERENCES tecnico(id_tecnico),
    FOREIGN KEY (id_estado_asignacion) REFERENCES estado_asignacion(id_estado_asignacion)
);

-- 4.2 EVIDENCIA (fotos, audios, texto)
CREATE TABLE evidencia (
    id_evidencia        SERIAL PRIMARY KEY,
    id_incidente        INT          NOT NULL,
    id_tipo_evidencia   INT          NOT NULL,          -- imagen | audio | texto
    url_archivo         VARCHAR(500) NOT NULL,          -- URL en almacenamiento (S3, GCS, etc.)
    transcripcion_audio TEXT,                           -- resultado del módulo de speech-to-text
    descripcion_ia      TEXT,                           -- análisis de imagen por visión artificial
    created_at          TIMESTAMP    NOT NULL DEFAULT NOW(),
    FOREIGN KEY (id_incidente)      REFERENCES incidente(id_incidente),
    FOREIGN KEY (id_tipo_evidencia) REFERENCES tipo_evidencia(id_tipo_evidencia)
);

-- 4.3 HISTORIAL DE ESTADOS del incidente
CREATE TABLE historial_estado_incidente (
    id_historial        SERIAL PRIMARY KEY,
    id_incidente        INT          NOT NULL,
    id_estado_anterior  INT,                            -- NULL si es el estado inicial
    id_estado_nuevo     INT          NOT NULL,
    observacion         VARCHAR(500),
    created_at          TIMESTAMP    NOT NULL DEFAULT NOW(),
    FOREIGN KEY (id_incidente)       REFERENCES incidente(id_incidente),
    FOREIGN KEY (id_estado_anterior) REFERENCES estado_incidente(id_estado),
    FOREIGN KEY (id_estado_nuevo)    REFERENCES estado_incidente(id_estado)
);

-- 4.4 HISTORIAL DE ESTADOS de la asignación
CREATE TABLE historial_estado_asignacion (
    id_historial        SERIAL PRIMARY KEY,
    id_asignacion       INT          NOT NULL,
    id_estado_anterior  INT,
    id_estado_nuevo     INT          NOT NULL,
    observacion         VARCHAR(500),
    created_at          TIMESTAMP    NOT NULL DEFAULT NOW(),
    FOREIGN KEY (id_asignacion)      REFERENCES asignacion(id_asignacion),
    FOREIGN KEY (id_estado_anterior) REFERENCES estado_asignacion(id_estado_asignacion),
    FOREIGN KEY (id_estado_nuevo)    REFERENCES estado_asignacion(id_estado_asignacion)
);


-- ==========================================
-- 5. NOTIFICACIONES, PAGOS Y MÉTRICAS
-- ==========================================

-- 5.1 NOTIFICACION
CREATE TABLE notificacion (
    id_notificacion     SERIAL PRIMARY KEY,
    id_usuario          INT,                            -- NULL si el destino es un taller
    id_taller           INT,                            -- NULL si el destino es un usuario
    id_incidente        INT,
    titulo              VARCHAR(100) NOT NULL,
    mensaje             TEXT         NOT NULL,
    leido               BOOLEAN      NOT NULL DEFAULT FALSE,
    enviado_push        BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMP    NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_notif_destino CHECK (
        (id_usuario IS NOT NULL AND id_taller IS NULL) OR
        (id_usuario IS NULL AND id_taller IS NOT NULL)
    ),
    FOREIGN KEY (id_usuario)   REFERENCES usuario(id_usuario),
    FOREIGN KEY (id_taller)    REFERENCES taller(id_taller),
    FOREIGN KEY (id_incidente) REFERENCES incidente(id_incidente)
);

-- 5.2 PAGO
CREATE TABLE pago (
    id_pago             SERIAL PRIMARY KEY,
    id_incidente        INT          NOT NULL,
    id_metodo_pago      INT          NOT NULL,
    id_estado_pago      INT          NOT NULL,
    monto_total         DECIMAL(10,2) NOT NULL,
    comision_plataforma DECIMAL(10,2) NOT NULL,         -- 10% del monto_total
    monto_taller        DECIMAL(10,2) NOT NULL,         -- 90% del monto_total
    referencia_externa  VARCHAR(100),                   -- ID de transacción de la pasarela
    created_at          TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP    NOT NULL DEFAULT NOW(),
    FOREIGN KEY (id_incidente)   REFERENCES incidente(id_incidente),
    FOREIGN KEY (id_metodo_pago) REFERENCES metodo_pago(id_metodo_pago),
    FOREIGN KEY (id_estado_pago) REFERENCES estado_pago(id_estado_pago)
);

-- 5.3 MÉTRICA (KPIs por incidente)
CREATE TABLE metrica (
    id_metrica              SERIAL PRIMARY KEY,
    id_incidente            INT NOT NULL UNIQUE,
    fecha_inicio            TIMESTAMP,                  -- cuando el usuario reportó
    fecha_asignacion        TIMESTAMP,                  -- cuando se asignó el taller
    fecha_llegada_tecnico   TIMESTAMP,                  -- cuando el técnico llegó
    fecha_fin               TIMESTAMP,                  -- cuando se marcó como atendido
    tiempo_respuesta_min    INT,                        -- fecha_asignacion - fecha_inicio
    tiempo_llegada_min      INT,                        -- fecha_llegada - fecha_asignacion
    tiempo_resolucion_min   INT,                        -- fecha_fin - fecha_inicio
    calificacion_cliente    INT,                        -- 1 a 5 estrellas
    comentario_cliente      TEXT,
    FOREIGN KEY (id_incidente) REFERENCES incidente(id_incidente)
);

-- 5.4 CANDIDATO_ASIGNACION (log del motor de asignación inteligente)
CREATE TABLE candidato_asignacion (
    id_candidato        SERIAL PRIMARY KEY,
    id_incidente        INT          NOT NULL,
    id_taller           INT          NOT NULL,
    distancia_km        DOUBLE PRECISION,
    score_total         DOUBLE PRECISION,               -- puntaje calculado por el motor
    seleccionado        BOOLEAN      NOT NULL DEFAULT FALSE,
    motivo_rechazo      VARCHAR(255),
    created_at          TIMESTAMP    NOT NULL DEFAULT NOW(),
    FOREIGN KEY (id_incidente) REFERENCES incidente(id_incidente),
    FOREIGN KEY (id_taller)    REFERENCES taller(id_taller)
);

-- 5.5 MENSAJE (chat opcional entre cliente y taller)
CREATE TABLE mensaje (
    id_mensaje          SERIAL PRIMARY KEY,
    id_incidente        INT          NOT NULL,
    id_usuario          INT,                            -- NULL si lo envía el taller
    id_taller           INT,                            -- NULL si lo envía el usuario
    contenido           TEXT         NOT NULL,
    leido               BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMP    NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_msg_origen CHECK (
        (id_usuario IS NOT NULL AND id_taller IS NULL) OR
        (id_usuario IS NULL AND id_taller IS NOT NULL)
    ),
    FOREIGN KEY (id_incidente) REFERENCES incidente(id_incidente),
    FOREIGN KEY (id_usuario)   REFERENCES usuario(id_usuario),
    FOREIGN KEY (id_taller)    REFERENCES taller(id_taller)
);


-- ==========================================
-- 6. ÍNDICES PARA RENDIMIENTO
-- ==========================================

CREATE INDEX ix_incidente_usuario    ON incidente(id_usuario);
CREATE INDEX ix_incidente_estado     ON incidente(id_estado);
CREATE INDEX ix_asignacion_incidente ON asignacion(id_incidente);
CREATE INDEX ix_asignacion_taller    ON asignacion(id_taller);
CREATE INDEX ix_evidencia_incidente  ON evidencia(id_incidente);
CREATE INDEX ix_notif_usuario        ON notificacion(id_usuario);
CREATE INDEX ix_notif_taller         ON notificacion(id_taller);
CREATE INDEX ix_vehiculo_usuario     ON vehiculo(id_usuario);
CREATE INDEX ix_tecnico_taller       ON tecnico(id_taller);
CREATE INDEX ix_mensaje_incidente    ON mensaje(id_incidente);
CREATE INDEX ix_candidato_incidente  ON candidato_asignacion(id_incidente);
