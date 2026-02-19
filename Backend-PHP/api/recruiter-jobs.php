<?php
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

function ensureRequiredSkillsColumn(PDO $db): void {
    try {
        $db->exec("ALTER TABLE jobs ADD COLUMN required_skills TEXT NULL");
    } catch (PDOException $e) {
        $message = strtolower($e->getMessage());
        if (strpos($message, 'duplicate column') === false && strpos($message, '1060') === false) {
            throw $e;
        }
    }
}

$recruiter_id = $_GET['recruiter_id'] ?? null;

if (!$recruiter_id) {
    echo json_encode(["success" => false, "message" => "Recruiter ID required"]);
    exit();
}

try {
    $database = new Database();
    $db = $database->getConnection();
    ensureAcceptingApplicationsColumn($db);
    ensureRequiredSkillsColumn($db);

    $query = "
        SELECT
            j.*,
            COALESCE(NULLIF(TRIM(rp.company_name), ''), u.email) AS company_name
        FROM jobs j
        JOIN users u ON u.id = j.recruiter_id
        LEFT JOIN recruiter_profiles rp ON rp.user_id = j.recruiter_id
        WHERE j.recruiter_id = ?
        ORDER BY j.created_at DESC
    ";
    $stmt = $db->prepare($query);
    $stmt->execute([$recruiter_id]);

    $jobs = $stmt->fetchAll(PDO::FETCH_ASSOC);
    echo json_encode(["success" => true, "jobs" => $jobs]);
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode(["success" => false, "message" => "Failed to fetch recruiter jobs"]);
}
?>
