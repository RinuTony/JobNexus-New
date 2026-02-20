<?php
error_reporting(E_ALL);
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);

header("Content-Type: application/json");

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode([
        'success' => false,
        'message' => 'Invalid request method. Use POST.'
    ]);
    exit();
}

require_once __DIR__ . '/../config/database.php';
require_once __DIR__ . '/auth.php';

try {
    $database = new Database();
    $db = $database->getConnection();
    $authUser = require_auth($db);
    require_roles($authUser, ['admin', 'database_admin']);

    $candidateId = (int)($_POST['candidate_id'] ?? 0);
    if ($candidateId <= 0) {
        auth_json_error(400, 'candidate_id is required');
    }

    if (!isset($_FILES['resume']) || $_FILES['resume']['error'] !== UPLOAD_ERR_OK) {
        auth_json_error(400, 'Resume upload failed');
    }

    $fileName = $_FILES['resume']['name'] ?? '';
    $fileExt = strtolower(pathinfo($fileName, PATHINFO_EXTENSION));
    $allowed = ['pdf', 'doc', 'docx', 'txt'];
    if (!in_array($fileExt, $allowed, true)) {
        auth_json_error(400, 'Unsupported file type');
    }

    if ((int)($_FILES['resume']['size'] ?? 0) > 10 * 1024 * 1024) {
        auth_json_error(400, 'File exceeds 10MB limit');
    }

    $uploadDir = __DIR__ . "/../uploads/";
    if (!is_dir($uploadDir)) {
        mkdir($uploadDir, 0777, true);
    }

    $storedName = uniqid("resume_", true) . "." . $fileExt;
    $target = $uploadDir . $storedName;
    if (!move_uploaded_file($_FILES['resume']['tmp_name'], $target)) {
        throw new Exception('Failed to move uploaded file');
    }

    $displayName = trim((string)($_POST['display_name'] ?? ''));
    if ($displayName === '') {
        $displayName = pathinfo($fileName, PATHINFO_FILENAME);
    }

    $stmt = $db->prepare("
        INSERT INTO candidate_resumes (candidate_id, resume_filename, display_name, uploaded_at)
        VALUES (:candidate_id, :resume_filename, :display_name, NOW())
    ");
    $stmt->execute([
        ':candidate_id' => $candidateId,
        ':resume_filename' => $storedName,
        ':display_name' => $displayName
    ]);

    echo json_encode([
        'success' => true,
        'message' => 'Resume uploaded successfully',
        'resume_filename' => $storedName
    ]);
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'message' => $e->getMessage()
    ]);
}

