

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

-- DONNÉES DE TEST

-- Admin
INSERT INTO Utilisateur (nom, prenom, email, mdp, role)
VALUES ('Rahajarison', 'Hasina', 'admin@diamada.mg', 'hashed_admin', 'admin');

INSERT INTO Admin (id, niveau_acces) VALUES (1, 'super_admin');

-- Passagers
INSERT INTO Utilisateur (nom, prenom, email, mdp, role) VALUES
('Rakoto', 'Jean', 'jean@mail.mg', 'hashed1', 'passager'),
('Rabe', 'Marie', 'marie@mail.mg', 'hashed2', 'passager');

INSERT INTO Passager (id, num_tel) VALUES
(2, '+261340000001'),
(3, '+261340000002');

-- Vehicules
INSERT INTO Vehicule (immatriculation, capacite) VALUES
('MG-1234-T', 15),
('MG-5678-T', 12);

-- Trajets
INSERT INTO Trajet (ville_depart, destination, date, heure, prix, places_disponibles, id_vehicule) VALUES
('Antananarivo', 'Toamasina', '2025-06-01', '06:00:00', 15000, 15, 1),
('Antananarivo', 'Fianarantsoa', '2025-06-01', '05:30:00', 12000, 12, 2);

-- Reservations
INSERT INTO Reservation (id_passager, id_trajet, nb_places, statut) VALUES
(2, 1, 2, 'confirmee'),
(3, 1, 1, 'confirmee');

-- Mise à jour des places (CORRIGÉ)
UPDATE Trajet SET places_disponibles = places_disponibles - 2 WHERE id = 1;
UPDATE Trajet SET places_disponibles = places_disponibles - 1 WHERE id = 1;

-- VUE : Trajets disponibles
CREATE VIEW vue_trajets_disponibles AS
SELECT
    t.id,
    t.ville_depart,
    t.destination,
    t.date,
    t.heure,
    t.prix,
    t.places_disponibles,
    v.capacite,
    ROUND((1 - t.places_disponibles / v.capacite) * 100, 1) AS taux_remplissage
FROM Trajet t
JOIN Vehicule v ON t.id_vehicule = v.id
WHERE t.statut = 'planifie'
  AND t.places_disponibles > 0;

-- VUE : Réservations passager
CREATE VIEW vue_reservations_passager AS
SELECT
    r.id,
    CONCAT(u.prenom, ' ', u.nom) AS passager,
    t.ville_depart,
    t.destination,
    t.date,
    t.heure,
    r.nb_places,
    (t.prix * r.nb_places) AS total,
    r.statut
FROM Reservation r
JOIN Passager p ON r.id_passager = p.id
JOIN Utilisateur u ON u.id = p.id
JOIN Trajet t ON r.id_trajet = t.id;

-- VUE : Statistiques (CORRIGÉ)
CREATE VIEW vue_statistiques AS
SELECT
    (SELECT COUNT(*) FROM Utilisateur) AS nb_utilisateurs,
    (SELECT COUNT(*) FROM Reservation) AS nb_reservations,
    (SELECT COUNT(*) FROM Trajet) AS nb_trajets,
    (
        SELECT ROUND(AVG((v.capacite - t.places_disponibles)/v.capacite)*100,1)
        FROM Trajet t
        JOIN Vehicule v ON t.id_vehicule = v.id
    ) AS taux_remplissage_moyen;