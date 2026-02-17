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

function notifyAppliedCandidates(PDO $db, int $jobId, string $status, string $message): void {
    $appsStmt = $db->prepare("
        SELECT id, candidate_id
        FROM applications
        WHERE job_id = :job_id
        ORDER BY id DESC
    ");
    $appsStmt->execute([':job_id' => $jobId]);
    $applications = $appsStmt->fetchAll(PDO::FETCH_ASSOC);

    $seenCandidates = [];
    $notifyStmt = $db->prepare("
        INSERT INTO notifications (user_id, application_id, job_id, status, message, is_read, created_at)
        VALUES (:user_id, :application_id, :job_id, :status, :message, 0, NOW())
    ");

    foreach ($applications as $app) {
        $candidateId = (int)($app['candidate_id'] ?? 0);
        if (!$candidateId || isset($seenCandidates[$candidateId])) {
            continue;
        }
        $seenCandidates[$candidateId] = true;
        $notifyStmt->execute([
            ':user_id' => $candidateId,
            ':application_id' => (int)$app['id'],
            ':job_id' => $jobId,
            ':status' => $status,
            ':message' => $message
        ]);
    }
}

$input = json_decode(file_get_contents("php://input"), true);
$jobId = (int)($input['job_id'] ?? 0);
$recruiterId = (int)($input['recruiter_id'] ?? 0);
$acceptingApplications = isset($input['accepting_applications']) ? (int)((bool)$input['accepting_applications']) : null;

if (!$jobId || !$recruiterId || $acceptingApplications === null) {
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
    ensureAcceptingApplicationsColumn($db);

    $verify = $db->prepare("SELECT id, title FROM jobs WHERE id = :job_id AND recruiter_id = :recruiter_id");
    $verify->execute([
        ':job_id' => $jobId,
        ':recruiter_id' => $recruiterId
    ]);
    $job = $verify->fetch(PDO::FETCH_ASSOC);

    if (!$job) {
        http_response_code(403);
        echo json_encode([
            "success" => false,
            "message" => "You don't have permission to modify this job"
        ]);
        exit();
    }

    $stmt = $db->prepare("
        UPDATE jobs
        SET accepting_applications = :accepting_applications
        WHERE id = :job_id AND recruiter_id = :recruiter_id
    ");
    $stmt->execute([
        ':accepting_applications' => $acceptingApplications,
        ':job_id' => $jobId,
        ':recruiter_id' => $recruiterId
    ]);

    $status = $acceptingApplications ? 'job_reopened' : 'job_closed';
    $message = $acceptingApplications
        ? "Applications reopened for {$job['title']}."
        : "Applications are now closed for {$job['title']}.";
    notifyAppliedCandidates($db, $jobId, $status, $message);

    echo json_encode([
        "success" => true,
        "message" => $acceptingApplications ? "Job reopened for applications" : "Job closed for applications",
        "accepting_applications" => $acceptingApplications
    ]);
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        "success" => false,
        "message" => "Failed to update job application state"
    ]);
}
?>
