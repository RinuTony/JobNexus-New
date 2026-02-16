<?php
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);
error_reporting(E_ALL);

header("Content-Type: application/json");
header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Methods: POST, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type");

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode([
        "success" => false,
        "message" => "Method not allowed"
    ]);
    exit;
}

require_once __DIR__ . '/../config/database.php';

try {
    $input = json_decode(file_get_contents('php://input'), true);
    $user_id = $input['user_id'] ?? null;
    $resume_id = $input['resume_id'] ?? null;
    $new_title = $input['new_title'] ?? null;

    if (!$user_id || !$resume_id || !$new_title) {
        throw new Exception("Missing user_id, resume_id, or new_title");
    }

    $new_title = trim($new_title);
    if ($new_title === "") {
        throw new Exception("New title cannot be empty");
    }

    if (strlen($new_title) > 255) {
        $new_title = substr($new_title, 0, 255);
    }

    $database = new Database();
    $db = $database->getConnection();
    if (!$db) {
        throw new Exception("Database connection failed");
    }

    $check = $db->prepare(
        "SELECT id FROM resumes WHERE id = :id AND user_id = :user_id LIMIT 1"
    );
    $check->execute([
        ':id' => $resume_id,
        ':user_id' => $user_id
    ]);
    $row = $check->fetch(PDO::FETCH_ASSOC);
    if (!$row) {
        throw new Exception("Resume not found for user");
    }

    $stmt = $db->prepare(
        "UPDATE resumes SET title = :title, updated_at = NOW() WHERE id = :id AND user_id = :user_id"
    );
    $stmt->execute([
        ':title' => $new_title,
        ':id' => $resume_id,
        ':user_id' => $user_id
    ]);

    echo json_encode([
        "success" => true,
        "message" => "Resume renamed",
        "title" => $new_title
    ]);

} catch (Exception $e) {
    http_response_code(400);
    echo json_encode([
        "success" => false,
        "message" => $e->getMessage()
    ]);
}
?>
