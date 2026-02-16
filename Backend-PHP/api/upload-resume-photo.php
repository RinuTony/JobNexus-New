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

try {
    $candidate_id = $_POST['candidate_id'] ?? null;
    if (!$candidate_id) {
        throw new Exception("Missing candidate_id");
    }

    if (!isset($_FILES['photo']) || $_FILES['photo']['error'] !== UPLOAD_ERR_OK) {
        throw new Exception("Photo upload failed");
    }

    $uploadDir = __DIR__ . "/../uploads/resume-photos/";
    if (!is_dir($uploadDir)) {
        mkdir($uploadDir, 0777, true);
    }

    $originalName = $_FILES['photo']['name'] ?? '';
    $originalName = basename($originalName);
    $fileExt = strtolower(pathinfo($originalName, PATHINFO_EXTENSION));
    $allowed = ['jpg', 'jpeg', 'png', 'gif', 'webp'];
    if (!in_array($fileExt, $allowed)) {
        throw new Exception("Invalid file type");
    }

    if ($_FILES['photo']['size'] > 5 * 1024 * 1024) {
        throw new Exception("File too large (max 5MB)");
    }

    $filename = "photo_" . $candidate_id . "_" . uniqid() . "." . $fileExt;
    $target = $uploadDir . $filename;

    if (!move_uploaded_file($_FILES['photo']['tmp_name'], $target)) {
        throw new Exception("Failed to save file");
    }

    $photoUrl = "http://localhost/JobNexus/Backend-PHP/uploads/resume-photos/" . $filename;

    echo json_encode([
        "success" => true,
        "message" => "Photo uploaded successfully",
        "photo_url" => $photoUrl
    ]);

} catch (Exception $e) {
    http_response_code(400);
    echo json_encode([
        "success" => false,
        "message" => $e->getMessage()
    ]);
}
?>
