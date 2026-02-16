<?php
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);
error_reporting(E_ALL);

header("Content-Type: application/json");

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
    $new_name = $input['new_name'] ?? null;

    if (!$candidate_id || !$resume_filename || !$new_name) {
        throw new Exception("Missing candidate_id, resume_filename, or new_name");
    }

    $safe_name = basename($resume_filename);
    if ($safe_name !== $resume_filename) {
        throw new Exception("Invalid resume filename");
    }

    $new_name = trim($new_name);
    if ($new_name === "") {
        throw new Exception("New name cannot be empty");
    }

    // Ensure extension is present (use existing file extension if missing)
    $existing_ext = pathinfo($resume_filename, PATHINFO_EXTENSION);
    $new_ext = pathinfo($new_name, PATHINFO_EXTENSION);
    if ($existing_ext && !$new_ext) {
        $new_name = $new_name . "." . $existing_ext;
    }

    // Basic length cap
    if (strlen($new_name) > 255) {
        $new_name = substr($new_name, 0, 255);
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

    $stmt = $db->prepare(
        "UPDATE candidate_resumes SET display_name = :display_name WHERE candidate_id = :candidate_id AND resume_filename = :resume_filename"
    );
    $stmt->execute([
        ':display_name' => $new_name,
        ':candidate_id' => $candidate_id,
        ':resume_filename' => $resume_filename
    ]);

    echo json_encode([
        "success" => true,
        "message" => "Resume renamed",
        "display_name" => $new_name
    ]);

} catch (Exception $e) {
    http_response_code(400);
    echo json_encode([
        "success" => false,
        "message" => $e->getMessage()
    ]);
}
?>
