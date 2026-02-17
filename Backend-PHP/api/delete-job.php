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
    echo json_encode([
        "success" => false,
        "message" => "Invalid request method"
    ]);
    exit();
}

require_once __DIR__ . '/../config/database.php';

$input = json_decode(file_get_contents("php://input"), true);
$jobId = (int)($input['job_id'] ?? 0);
$recruiterId = (int)($input['recruiter_id'] ?? 0);

if (!$jobId || !$recruiterId) {
    http_response_code(400);
    echo json_encode([
        "success" => false,
        "message" => "Missing required fields"
    ]);
    exit();
}

try {
    $database = new Database();
    $db = $database->getConnection();

    $verify = $db->prepare("SELECT id FROM jobs WHERE id = :job_id AND recruiter_id = :recruiter_id");
    $verify->execute([
        ':job_id' => $jobId,
        ':recruiter_id' => $recruiterId
    ]);
    if (!$verify->fetch()) {
        http_response_code(403);
        echo json_encode([
            "success" => false,
            "message" => "You don't have permission to delete this job"
        ]);
        exit();
    }

    $db->beginTransaction();
    $deleteApplications = $db->prepare("DELETE FROM applications WHERE job_id = :job_id");
    $deleteApplications->execute([':job_id' => $jobId]);

    $deleteJob = $db->prepare("DELETE FROM jobs WHERE id = :job_id AND recruiter_id = :recruiter_id");
    $deleteJob->execute([
        ':job_id' => $jobId,
        ':recruiter_id' => $recruiterId
    ]);
    $db->commit();

    echo json_encode([
        "success" => true,
        "message" => "Job deleted successfully"
    ]);
} catch (Exception $e) {
    if (isset($db) && $db->inTransaction()) {
        $db->rollBack();
    }
    http_response_code(500);
    echo json_encode([
        "success" => false,
        "message" => "Failed to delete job"
    ]);
}
?>
