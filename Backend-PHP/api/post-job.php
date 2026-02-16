<?php
error_reporting(E_ALL);
ini_set('display_errors', 1);

<<<<<<< HEAD
header("Access-Control-Allow-Origin: *");
=======
header("Access-Control-Allow-Origin: http://localhost:3000");
>>>>>>> upstream/main
header("Access-Control-Allow-Methods: POST, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type");
header("Content-Type: application/json");

<<<<<<< HEAD
=======
// Handle preflight
>>>>>>> upstream/main
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

<<<<<<< HEAD
require_once __DIR__ . '/../config/database.php';  // Updated path to go up one level
=======
require "config.php"; // this gives $pdo
>>>>>>> upstream/main

$input = json_decode(file_get_contents("php://input"), true);

if (
    !$input ||
    empty($input['title']) ||
    empty($input['description']) ||
    empty($input['recruiter_id'])
) {
    echo json_encode([
        "success" => false,
        "message" => "Missing required fields"
    ]);
    exit();
}

$title = trim($input['title']);
$description = trim($input['description']);
$recruiterId = (int)$input['recruiter_id'];

try {
<<<<<<< HEAD
    // ✅ Use Database class instead of direct PDO connection
    $database = new Database();
    $db = $database->getConnection();

    $stmt = $db->prepare("
        INSERT INTO jobs (title, description, recruiter_id, created_at)
        VALUES (:title, :description, :recruiter_id, NOW())
=======
    $stmt = $pdo->prepare("
        INSERT INTO jobs (title, description, recruiter_id)
        VALUES (:title, :description, :recruiter_id)
>>>>>>> upstream/main
    ");

    $stmt->execute([
        ":title" => $title,
        ":description" => $description,
        ":recruiter_id" => $recruiterId
    ]);

    echo json_encode([
        "success" => true,
<<<<<<< HEAD
        "message" => "Job posted successfully",
        "job_id" => $db->lastInsertId()
    ]);
} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode([
        "success" => false,
        "message" => "Failed to post job",
        "error" => $e->getMessage()
    ]);
}
=======
        "message" => "Job posted successfully"
    ]);
} catch (PDOException $e) {
    echo json_encode([
        "success" => false,
        "message" => $e->getMessage()
    ]);
}
>>>>>>> upstream/main
