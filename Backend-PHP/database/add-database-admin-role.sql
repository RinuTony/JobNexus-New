ALTER TABLE users
MODIFY role ENUM('candidate','recruiter','admin','database_admin') DEFAULT 'candidate';

