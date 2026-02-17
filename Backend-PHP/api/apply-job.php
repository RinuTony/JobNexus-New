<?php
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);
error_reporting(E_ALL);

header("Content-Type: application/json");

require_once __DIR__ . '/../config/database.php';

function ensureAcceptingApplicationsColumn(PDO $db): void {
    try {
        $db->exec("ALTER TABLE jobs ADD COLUMN accepting_applications TINYINT(1) NOT NULL DEFAULT 1");
    } catch (PDOException $e) {
        $message = strtolower($e->getMessage());
        if (strpos($message, 'duplicate column') === false && strpos($message, '1060') === false) {
            throw $e;
        }
    }
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
    $database = new Database();
    $db = $database->getConnection();
    ensureAcceptingApplicationsColumn($db);

    $job_id = $_POST['job_id'] ?? null;
    $candidate_id = $_POST['candidate_id'] ?? null;

    if (!$job_id || !$candidate_id) {
        throw new Exception("Missing required fields");
    }

    if (!isset($_FILES['resume']) || $_FILES['resume']['error'] !== UPLOAD_ERR_OK) {
        throw new Exception("Resume upload failed");
    }

    $uploadDir = __DIR__ . "/../uploads/";
    if (!is_dir($uploadDir)) {
        mkdir($uploadDir, 0777, true);
    }

    $fileExt = strtolower(pathinfo($_FILES['resume']['name'], PATHINFO_EXTENSION));
    $allowed = ['pdf', 'doc', 'docx', 'txt'];

    if (!in_array($fileExt, $allowed, true)) {
        throw new Exception("Invalid file type");
    }

    if ($_FILES['resume']['size'] > 10 * 1024 * 1024) {
        throw new Exception("File too large (max 10MB)");
    }

    $jobStmt = $db->prepare("SELECT title, recruiter_id, accepting_applications FROM jobs WHERE id = ?");
    $jobStmt->execute([$job_id]);
    $job = $jobStmt->fetch(PDO::FETCH_ASSOC);

    if (!$job) {
        throw new Exception("Job not found");
    }

    if ((int)($job['accepting_applications'] ?? 1) !== 1) {
        throw new Exception("This job is no longer accepting applications");
    }

    $filename = uniqid("resume_", true) . "." . $fileExt;
    $target = $uploadDir . $filename;

    if (!move_uploaded_file($_FILES['resume']['tmp_name'], $target)) {
        throw new Exception("Failed to save file");
    }

    $check = $db->prepare("SELECT id FROM applications WHERE job_id = ? AND candidate_id = ?");
    $check->execute([$job_id, $candidate_id]);

    if ($check->rowCount() > 0) {
        unlink($target);
        throw new Exception("Already applied for this job");
    }

    $stmt = $db->prepare("
        INSERT INTO applications
        (job_id, candidate_id, resume_filename, status, applied_at)
        VALUES (?, ?, ?, 'pending', NOW())
    ");

    $stmt->execute([$job_id, $candidate_id, $filename]);
    $applicationId = $db->lastInsertId();

    if ($job && !empty($job['recruiter_id'])) {
        $message = "New application for " . ($job['title'] ?? 'your job') . ".";
        $notifyStmt = $db->prepare("
            INSERT INTO notifications (user_id, application_id, job_id, status, message, is_read, created_at)
            VALUES (?, ?, ?, 'applied', ?, 0, NOW())
        ");
        $notifyStmt->execute([
            $job['recruiter_id'],
            $applicationId,
            $job_id,
            $message
        ]);
    }

    echo json_encode([
        "success" => true,
        "message" => "Application submitted successfully"
    ]);
} catch (Exception $e) {
    http_response_code(400);
    echo json_encode([
        "success" => false,
        "message" => $e->getMessage()
    ]);
}
?>
