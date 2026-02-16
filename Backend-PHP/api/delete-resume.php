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
    $candidate_id = $input['candidate_id'] ?? null;
    $resume_filename = $input['resume_filename'] ?? null;

    if (!$candidate_id || !$resume_filename) {
        throw new Exception("Missing candidate_id or resume_filename");
    }

    $safe_name = basename($resume_filename);
    if ($safe_name !== $resume_filename) {
        throw new Exception("Invalid resume filename");
    }

    $database = new Database();
    $db = $database->getConnection();
    if (!$db) {
        throw new Exception("Database connection failed");
    }

    // Verify ownership
    $check = $db->prepare(
        "SELECT id FROM candidate_resumes WHERE candidate_id = :candidate_id AND resume_filename = :resume_filename LIMIT 1"
    );
    $check->execute([
        ':candidate_id' => $candidate_id,
        ':resume_filename' => $resume_filename
    ]);
    $row = $check->fetch(PDO::FETCH_ASSOC);
    if (!$row) {
        throw new Exception("Resume not found for candidate");
    }

    // Delete DB record
    $del = $db->prepare(
        "DELETE FROM candidate_resumes WHERE candidate_id = :candidate_id AND resume_filename = :resume_filename"
    );
    $del->execute([
        ':candidate_id' => $candidate_id,
        ':resume_filename' => $resume_filename
    ]);

    // Only delete file if it's not referenced by applications
    $ref = $db->prepare(
        "SELECT 1 FROM applications WHERE candidate_id = :candidate_id AND resume_filename = :resume_filename LIMIT 1"
    );
    $ref->execute([
        ':candidate_id' => $candidate_id,
        ':resume_filename' => $resume_filename
    ]);
    $referenced = (bool)$ref->fetch(PDO::FETCH_ASSOC);

    $fileDeleted = false;
    if (!$referenced) {
        $uploadDir = __DIR__ . "/../uploads/";
        $target = $uploadDir . $resume_filename;
        if (is_file($target)) {
            $fileDeleted = unlink($target);
        }
    }

    echo json_encode([
        "success" => true,
        "message" => "Resume deleted",
        "file_deleted" => $fileDeleted
    ]);

} catch (Exception $e) {
    http_response_code(400);
    echo json_encode([
        "success" => false,
        "message" => $e->getMessage()
    ]);
}
?>
