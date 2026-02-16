<?php
// api/download-resume.php

ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);
error_reporting(E_ALL);

header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Methods: GET, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type");

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

require_once __DIR__ . '/../config/database.php';

$application_id = $_GET['application_id'] ?? null;
$resume_filename = $_GET['filename'] ?? null;
$recruiter_id = $_GET['recruiter_id'] ?? null;

// Validate inputs
if (!$application_id && !$resume_filename) {
    http_response_code(400);
    echo json_encode([
        "success" => false,
        "message" => "Either application_id or filename is required"
    ]);
    exit();
}

try {
    $database = new Database();
    $db = $database->getConnection();

    // If application_id is provided, verify the recruiter has access
    if ($application_id && $recruiter_id) {
        $checkQuery = "
            SELECT a.resume_filename 
            FROM applications a
            JOIN jobs j ON a.job_id = j.id
            WHERE a.id = ? AND j.recruiter_id = ?
        ";
        
        $checkStmt = $db->prepare($checkQuery);
        $checkStmt->execute([$application_id, $recruiter_id]);
        $result = $checkStmt->fetch();
        
        if (!$result || empty($result['resume_filename'])) {
            http_response_code(404);
            echo json_encode([
                "success" => false,
                "message" => "Resume not found or access denied"
            ]);
            exit();
        }
        
        $resume_filename = $result['resume_filename'];
    }
    
    // Validate filename format
    if (!preg_match('/^resume_[a-zA-Z0-9_\-\.]+\.(pdf|doc|docx|txt)$/', $resume_filename)) {
        http_response_code(400);
        echo json_encode([
            "success" => false,
            "message" => "Invalid filename format"
        ]);
        exit();
    }

    // Path to resume file
    $uploadDir = __DIR__ . "/../uploads/";
    $filePath = $uploadDir . $resume_filename;

    // Check if file exists
    if (!file_exists($filePath)) {
        http_response_code(404);
        echo json_encode([
            "success" => false,
            "message" => "Resume file not found"
        ]);
        exit();
    }

    // Get file info
    $fileSize = filesize($filePath);
    $fileExtension = pathinfo($filePath, PATHINFO_EXTENSION);
    
    // Set appropriate content type
    $contentTypes = [
        'pdf' => 'application/pdf',
        'doc' => 'application/msword',
        'docx' => 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'txt' => 'text/plain'
    ];
    
    $contentType = $contentTypes[$fileExtension] ?? 'application/octet-stream';

    // Send file to browser
    header('Content-Type: ' . $contentType);
    header('Content-Disposition: inline; filename="' . basename($filePath) . '"');
    header('Content-Length: ' . $fileSize);
    header('Cache-Control: private, max-age=0, must-revalidate');
    header('Pragma: public');
    
    readfile($filePath);
    exit;

} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        "success" => false,
        "message" => "Failed to retrieve resume",
        "error" => $e->getMessage()
    ]);
}
?>