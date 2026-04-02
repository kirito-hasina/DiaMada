

CREATE DATABASE IF NOT EXISTS diamada ;
USE diamada;

-- TABLE : Utilisateur
CREATE TABLE Utilisateur (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    nom         VARCHAR(100) NOT NULL,
    prenom      VARCHAR(100) NOT NULL,
    email       VARCHAR(150) NOT NULL UNIQUE,
    mdp         VARCHAR(255) NOT NULL,
    role        ENUM('passager', 'admin') NOT NULL DEFAULT 'passager',
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- TABLE : Passager
CREATE TABLE Passager (
    id          INT PRIMARY KEY,
    num_tel     VARCHAR(20) NOT NULL,
    FOREIGN KEY (id) REFERENCES Utilisateur(id)
        ON DELETE CASCADE ON UPDATE CASCADE
);

-- TABLE : Admin
CREATE TABLE Admin (
    id              INT PRIMARY KEY,
    niveau_acces    VARCHAR(50) NOT NULL DEFAULT 'standard',
    FOREIGN KEY (id) REFERENCES Utilisateur(id)
        ON DELETE CASCADE ON UPDATE CASCADE
);

-- TABLE : Vehicule
CREATE TABLE Vehicule (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    immatriculation     VARCHAR(20) NOT NULL UNIQUE,
    capacite            INT NOT NULL CHECK (capacite > 0)
);

-- TABLE : Trajet (CORRIGÉ)
CREATE TABLE Trajet (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    ville_depart        VARCHAR(100) NOT NULL,
    destination         VARCHAR(100) NOT NULL,
    date                DATE NOT NULL,
    heure               TIME NOT NULL,
    prix                DECIMAL(10,2) NOT NULL CHECK (prix >= 0),
    places_disponibles  INT NOT NULL,
    id_vehicule         INT NOT NULL,
    statut              ENUM('planifie', 'en_cours', 'termine', 'annule') DEFAULT 'planifie',
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (id_vehicule) REFERENCES Vehicule(id)
        ON DELETE RESTRICT ON UPDATE CASCADE
);

-- TABLE : Reservation
CREATE TABLE Reservation (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    id_passager         INT NOT NULL,
    id_trajet           INT NOT NULL,
    nb_places           INT NOT NULL CHECK (nb_places > 0),
    date_reservation    DATETIME DEFAULT CURRENT_TIMESTAMP,
    statut              ENUM('confirmee', 'annulee', 'en_attente') DEFAULT 'en_attente',

    FOREIGN KEY (id_passager) REFERENCES Passager(id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (id_trajet) REFERENCES Trajet(id)
        ON DELETE RESTRICT ON UPDATE CASCADE
);

-- INDEX
CREATE INDEX idx_trajet_depart_dest ON Trajet(ville_depart, destination);
CREATE INDEX idx_trajet_date ON Trajet(date);
CREATE INDEX idx_reservation_passager ON Reservation(id_passager);
CREATE INDEX idx_reservation_trajet ON Reservation(id_trajet);

