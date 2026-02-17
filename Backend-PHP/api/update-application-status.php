<?php
// api/update-application-status.php

ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);
error_reporting(E_ALL);

header("Content-Type: application/json");

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

require_once __DIR__ . '/../config/database.php';

$input = json_decode(file_get_contents('php://input'), true);

$application_id = $input['application_id'] ?? null;
$status = $input['status'] ?? null;
$recruiter_id = $input['recruiter_id'] ?? null;

if (!$application_id || !$status || !$recruiter_id) {
    http_response_code(400);
    echo json_encode([
        "success" => false,
        "message" => "Missing required fields"
    ]);
    exit();
}

// Validate status (aligned with candidate-facing workflow)
$normalizedStatus = strtolower(trim($status));
$normalizedStatus = str_replace([' ', '-'], '_', $normalizedStatus);
$statusMap = [
    'applied' => 'applied',
    'pending' => 'pending',
    'reviewed' => 'reviewed',
    'shortlisted' => 'reviewed',
    'interview_scheduled' => 'interview_scheduled',
    'interviewed' => 'interviewed',
    'accepted' => 'accepted',
    'rejected' => 'rejected'
];
if (!isset($statusMap[$normalizedStatus])) {
    http_response_code(400);
    echo json_encode([
        "success" => false,
        "message" => "Invalid status value"
    ]);
    exit();
}
$status = $statusMap[$normalizedStatus];

try {
    $database = new Database();
    $db = $database->getConnection();

    // Verify recruiter owns this application
    $checkQuery = "
        SELECT a.id 
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        WHERE a.id = ? AND j.recruiter_id = ?
    ";
    
    $checkStmt = $db->prepare($checkQuery);
    $checkStmt->execute([$application_id, $recruiter_id]);
    
    if ($checkStmt->rowCount() === 0) {
        http_response_code(403);
        echo json_encode([
            "success" => false,
            "message" => "You don't have permission to update this application"
        ]);
        exit();
    }

    // Update status
    $updateQuery = "UPDATE applications SET status = ? WHERE id = ?";
    $updateStmt = $db->prepare($updateQuery);
    $updateStmt->execute([$status, $application_id]);

    // Fetch candidate + job details for notification
    $detailsQuery = "
        SELECT a.candidate_id, a.job_id, j.title AS job_title
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        WHERE a.id = ?
    ";
    $detailsStmt = $db->prepare($detailsQuery);
    $detailsStmt->execute([$application_id]);
    $details = $detailsStmt->fetch(PDO::FETCH_ASSOC);

    if ($details) {
        $statusPhraseMap = [
            'applied' => 'applied',
            'pending' => 'marked as pending',
            'reviewed' => 'reviewed',
            'interview_scheduled' => 'scheduled for interview',
            'interviewed' => 'marked as interviewed',
            'accepted' => 'accepted',
            'rejected' => 'rejected'
        ];
        $statusPhrase = $statusPhraseMap[$status] ?? str_replace('_', ' ', $status);
        $message = "Your application for " . ($details['job_title'] ?? 'a job') . " has been " . $statusPhrase . ".";
        $insertQuery = "
            INSERT INTO notifications (user_id, application_id, job_id, status, message, is_read, created_at)
            VALUES (?, ?, ?, ?, ?, 0, NOW())
        ";
        $insertStmt = $db->prepare($insertQuery);
        $insertStmt->execute([
            $details['candidate_id'],
            $application_id,
            $details['job_id'],
            $status,
            $message
        ]);
    }

    echo json_encode([
        "success" => true,
        "message" => "Application status updated successfully"
    ]);

} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        "success" => false,
        "message" => "Failed to update application status",
        "error" => $e->getMessage()
    ]);
}
?>
