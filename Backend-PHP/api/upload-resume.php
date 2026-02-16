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
    $candidate_id = $_POST['candidate_id'] ?? null;
    if (!$candidate_id) {
        throw new Exception("Missing candidate_id");
    }

    if (!isset($_FILES['resume']) || $_FILES['resume']['error'] !== UPLOAD_ERR_OK) {
        throw new Exception("Resume upload failed");
    }

    $uploadDir = __DIR__ . "/../uploads/";
    if (!is_dir($uploadDir)) {
        mkdir($uploadDir, 0777, true);
    }

    $originalName = $_FILES['resume']['name'] ?? '';
    $originalName = basename($originalName);
    $fileExt = strtolower(pathinfo($originalName, PATHINFO_EXTENSION));
    $allowed = ['pdf', 'doc', 'docx', 'txt'];
    if (!in_array($fileExt, $allowed)) {
        throw new Exception("Invalid file type");
    }

    if ($_FILES['resume']['size'] > 10 * 1024 * 1024) {
        throw new Exception("File too large (max 10MB)");
    }

    $filename = uniqid("resume_", true) . "." . $fileExt;
    $target = $uploadDir . $filename;

    if (!move_uploaded_file($_FILES['resume']['tmp_name'], $target)) {
        throw new Exception("Failed to save file");
    }

    $database = new Database();
    $db = $database->getConnection();
    if (!$db) {
        throw new Exception("Database connection failed");
    }

    $displayName = $originalName ?: $filename;
    $stmt = $db->prepare(
        "INSERT INTO candidate_resumes (candidate_id, resume_filename, display_name, uploaded_at)
         VALUES (:candidate_id, :resume_filename, :display_name, NOW())"
    );
    $stmt->execute([
        ':candidate_id' => $candidate_id,
        ':resume_filename' => $filename,
        ':display_name' => $displayName
    ]);

    echo json_encode([
        "success" => true,
        "message" => "Resume uploaded successfully",
        "resume_filename" => $filename
    ]);

} catch (Exception $e) {
    http_response_code(400);
    echo json_encode([
        "success" => false,
        "message" => $e->getMessage()
    ]);
}
?>
