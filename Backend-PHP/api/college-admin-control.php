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

function ensure_admin_audit_table(PDO $db): void {
    $db->exec("
        CREATE TABLE IF NOT EXISTS admin_audit_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            admin_user_id INT NOT NULL,
            action VARCHAR(100) NOT NULL,
            details TEXT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_admin_user_id (admin_user_id),
            INDEX idx_action (action),
            INDEX idx_created_at (created_at)
        )
    ");
}

function log_admin_action(PDO $db, int $adminUserId, string $action, array $details = []): void {
    $stmt = $db->prepare("
        INSERT INTO admin_audit_logs (admin_user_id, action, details)
        VALUES (:admin_user_id, :action, :details)
    ");
    $stmt->execute([
        ':admin_user_id' => $adminUserId,
        ':action' => $action,
        ':details' => json_encode($details)
    ]);
}

function normalize_application_status(string $status): string {
    $normalized = strtolower(trim($status));
    $normalized = str_replace([' ', '-'], '_', $normalized);
    return $normalized;
}

try {
    $database = new Database();
    $db = $database->getConnection();
    ensure_admin_audit_table($db);

    $authUser = require_auth($db);
    require_roles($authUser, ['admin', 'database_admin']);

    $input = json_decode(file_get_contents('php://input'), true) ?: [];
    $action = (string)($input['action'] ?? '');

    if ($action === '') {
        auth_json_error(400, 'Action is required');
    }

    switch ($action) {
        case 'dashboard_metrics': {
            $counts = [];
            $counts['candidates'] = (int)$db->query("SELECT COUNT(*) FROM users WHERE role = 'candidate'")->fetchColumn();
            $counts['recruiters'] = (int)$db->query("SELECT COUNT(*) FROM users WHERE role = 'recruiter'")->fetchColumn();
            $counts['jobs'] = (int)$db->query("SELECT COUNT(*) FROM jobs")->fetchColumn();
            $counts['applications'] = (int)$db->query("SELECT COUNT(*) FROM applications")->fetchColumn();
            $counts['resumes_uploaded'] = (int)$db->query("SELECT COUNT(*) FROM candidate_resumes")->fetchColumn();

            $statusRows = $db->query("
                SELECT COALESCE(NULLIF(status, ''), 'pending') AS status, COUNT(*) AS count
                FROM applications
                GROUP BY COALESCE(NULLIF(status, ''), 'pending')
            ")->fetchAll(PDO::FETCH_ASSOC);

            $statusCounts = [
                'pending' => 0,
                'reviewed' => 0,
                'shortlisted' => 0,
                'rejected' => 0
            ];
            foreach ($statusRows as $row) {
                $k = strtolower((string)$row['status']);
                if (isset($statusCounts[$k])) {
                    $statusCounts[$k] = (int)$row['count'];
                }
            }

            $recentJobs = $db->query("
                SELECT
                    j.id,
                    j.title,
                    COALESCE(NULLIF(TRIM(rp.company_name), ''), u.email) AS company_name,
                    j.created_at
                FROM jobs j
                JOIN users u ON u.id = j.recruiter_id
                LEFT JOIN recruiter_profiles rp ON rp.user_id = j.recruiter_id
                ORDER BY j.created_at DESC
                LIMIT 5
            ")->fetchAll(PDO::FETCH_ASSOC);

            echo json_encode([
                'success' => true,
                'metrics' => $counts,
                'application_status' => $statusCounts,
                'recent_jobs' => $recentJobs
            ]);
            break;
        }

        case 'list_candidates': {
            $search = trim((string)($input['search'] ?? ''));
            $skill = trim((string)($input['skill'] ?? ''));
            $location = trim((string)($input['location'] ?? ''));
            $minExperience = isset($input['minExperience']) && $input['minExperience'] !== '' ? (int)$input['minExperience'] : null;
            $hasResume = isset($input['hasResume']) ? (int)((bool)$input['hasResume']) : null;
            $limit = max(1, min(500, (int)($input['limit'] ?? 100)));

            $where = ["u.role = 'candidate'"];
            $params = [];

            if ($search !== '') {
                $where[] = "(u.email LIKE :search OR p.first_name LIKE :search OR p.last_name LIKE :search)";
                $params[':search'] = '%' . $search . '%';
            }
            if ($skill !== '') {
                $where[] = "cp.skills LIKE :skill";
                $params[':skill'] = '%' . $skill . '%';
            }
            if ($location !== '') {
                $where[] = "cp.preferred_location LIKE :location";
                $params[':location'] = '%' . $location . '%';
            }
            if ($minExperience !== null) {
                $where[] = "COALESCE(cp.experience_years, 0) >= :min_exp";
                $params[':min_exp'] = $minExperience;
            }
            if ($hasResume !== null) {
                $where[] = $hasResume ? "COALESCE(r.resume_count, 0) > 0" : "COALESCE(r.resume_count, 0) = 0";
            }

            $sql = "
                SELECT
                    u.id AS candidate_id,
                    u.email,
                    p.first_name,
                    p.last_name,
                    p.phone,
                    cp.skills,
                    cp.preferred_location,
                    cp.experience_years,
                    cp.current_company,
                    COALESCE(r.resume_count, 0) AS resume_count,
                    COALESCE(a.application_count, 0) AS application_count
                FROM users u
                LEFT JOIN profiles p ON p.user_id = u.id
                LEFT JOIN candidate_profiles cp ON cp.user_id = u.id
                LEFT JOIN (
                    SELECT candidate_id, COUNT(*) AS resume_count
                    FROM candidate_resumes
                    GROUP BY candidate_id
                ) r ON r.candidate_id = u.id
                LEFT JOIN (
                    SELECT candidate_id, COUNT(*) AS application_count
                    FROM applications
                    GROUP BY candidate_id
                ) a ON a.candidate_id = u.id
                WHERE " . implode(' AND ', $where) . "
                ORDER BY u.id DESC
                LIMIT :limit
            ";

            $stmt = $db->prepare($sql);
            foreach ($params as $k => $v) {
                $stmt->bindValue($k, $v);
            }
            $stmt->bindValue(':limit', $limit, PDO::PARAM_INT);
            $stmt->execute();

            echo json_encode([
                'success' => true,
                'candidates' => $stmt->fetchAll(PDO::FETCH_ASSOC)
            ]);
            break;
        }

        case 'list_recruiters': {
            $rows = $db->query("
                SELECT
                    u.id AS recruiter_id,
                    u.email,
                    rp.company_name,
                    rp.industry,
                    rp.website,
                    COALESCE(j.job_count, 0) AS job_count,
                    COALESCE(a.application_count, 0) AS application_count
                FROM users u
                LEFT JOIN recruiter_profiles rp ON rp.user_id = u.id
                LEFT JOIN (
                    SELECT recruiter_id, COUNT(*) AS job_count
                    FROM jobs
                    GROUP BY recruiter_id
                ) j ON j.recruiter_id = u.id
                LEFT JOIN (
                    SELECT j.recruiter_id, COUNT(*) AS application_count
                    FROM applications a
                    JOIN jobs j ON j.id = a.job_id
                    GROUP BY j.recruiter_id
                ) a ON a.recruiter_id = u.id
                WHERE u.role = 'recruiter'
                ORDER BY u.id DESC
            ")->fetchAll(PDO::FETCH_ASSOC);

            echo json_encode([
                'success' => true,
                'recruiters' => $rows
            ]);
            break;
        }

        case 'list_jobs': {
            $rows = $db->query("
                SELECT
                    j.id,
                    j.title,
                    j.accepting_applications,
                    j.created_at,
                    COALESCE(NULLIF(TRIM(rp.company_name), ''), u.email) AS company_name,
                    u.id AS recruiter_id,
                    COALESCE(app.application_count, 0) AS application_count
                FROM jobs j
                JOIN users u ON u.id = j.recruiter_id
                LEFT JOIN recruiter_profiles rp ON rp.user_id = j.recruiter_id
                LEFT JOIN (
                    SELECT job_id, COUNT(*) AS application_count
                    FROM applications
                    GROUP BY job_id
                ) app ON app.job_id = j.id
                ORDER BY j.created_at DESC
            ")->fetchAll(PDO::FETCH_ASSOC);

            echo json_encode([
                'success' => true,
                'jobs' => $rows
            ]);
            break;
        }

        case 'list_applications': {
            $status = trim((string)($input['status'] ?? ''));
            $jobId = isset($input['jobId']) && $input['jobId'] !== '' ? (int)$input['jobId'] : null;
            $candidateId = isset($input['candidateId']) && $input['candidateId'] !== '' ? (int)$input['candidateId'] : null;
            $recruiterId = isset($input['recruiterId']) && $input['recruiterId'] !== '' ? (int)$input['recruiterId'] : null;
            $limit = max(1, min(1000, (int)($input['limit'] ?? 200)));

            $where = ['1=1'];
            $params = [];
            if ($status !== '') {
                $where[] = "COALESCE(NULLIF(a.status, ''), 'pending') = :status";
                $params[':status'] = normalize_application_status($status);
            }
            if ($jobId !== null) {
                $where[] = "a.job_id = :job_id";
                $params[':job_id'] = $jobId;
            }
            if ($candidateId !== null) {
                $where[] = "a.candidate_id = :candidate_id";
                $params[':candidate_id'] = $candidateId;
            }
            if ($recruiterId !== null) {
                $where[] = "j.recruiter_id = :recruiter_id";
                $params[':recruiter_id'] = $recruiterId;
            }

            $sql = "
                SELECT
                    a.id AS application_id,
                    a.job_id,
                    a.candidate_id,
                    COALESCE(NULLIF(a.status, ''), 'pending') AS status,
                    a.applied_at,
                    j.title AS job_title,
                    j.recruiter_id,
                    ru.email AS recruiter_email,
                    COALESCE(NULLIF(TRIM(rp.company_name), ''), ru.email) AS company_name,
                    cu.email AS candidate_email,
                    p.first_name,
                    p.last_name,
                    p.phone
                FROM applications a
                JOIN jobs j ON j.id = a.job_id
                JOIN users ru ON ru.id = j.recruiter_id
                LEFT JOIN recruiter_profiles rp ON rp.user_id = j.recruiter_id
                JOIN users cu ON cu.id = a.candidate_id
                LEFT JOIN profiles p ON p.user_id = a.candidate_id
                WHERE " . implode(' AND ', $where) . "
                ORDER BY a.applied_at DESC
                LIMIT :limit
            ";
            $stmt = $db->prepare($sql);
            foreach ($params as $k => $v) {
                $stmt->bindValue($k, $v);
            }
            $stmt->bindValue(':limit', $limit, PDO::PARAM_INT);
            $stmt->execute();

            echo json_encode([
                'success' => true,
                'applications' => $stmt->fetchAll(PDO::FETCH_ASSOC)
            ]);
            break;
        }

        case 'update_application_status': {
            $applicationId = (int)($input['applicationId'] ?? 0);
            $newStatus = normalize_application_status((string)($input['status'] ?? ''));
            $allowed = ['pending', 'reviewed', 'shortlisted', 'rejected'];

            if ($applicationId <= 0 || !in_array($newStatus, $allowed, true)) {
                auth_json_error(400, 'Invalid applicationId or status');
            }

            $db->beginTransaction();

            $stmt = $db->prepare("
                SELECT
                    a.id,
                    a.candidate_id,
                    a.job_id,
                    j.recruiter_id,
                    j.title
                FROM applications a
                JOIN jobs j ON j.id = a.job_id
                WHERE a.id = :id
                LIMIT 1
            ");
            $stmt->execute([':id' => $applicationId]);
            $app = $stmt->fetch(PDO::FETCH_ASSOC);
            if (!$app) {
                throw new Exception('Application not found');
            }

            $stmt = $db->prepare("UPDATE applications SET status = :status WHERE id = :id");
            $stmt->execute([
                ':status' => $newStatus,
                ':id' => $applicationId
            ]);

            $candidateMessage = "Your application for " . ($app['title'] ?? 'a job') . " is now " . $newStatus . ".";
            $insertNotice = $db->prepare("
                INSERT INTO notifications (user_id, application_id, job_id, status, message, is_read, created_at)
                VALUES (:user_id, :application_id, :job_id, :status, :message, 0, NOW())
            ");

            $insertNotice->execute([
                ':user_id' => (int)$app['candidate_id'],
                ':application_id' => $applicationId,
                ':job_id' => (int)$app['job_id'],
                ':status' => $newStatus,
                ':message' => $candidateMessage
            ]);

            $recruiterMessage = "College admin updated application #" . $applicationId . " to " . $newStatus . ".";
            $insertNotice->execute([
                ':user_id' => (int)$app['recruiter_id'],
                ':application_id' => $applicationId,
                ':job_id' => (int)$app['job_id'],
                ':status' => 'admin_update',
                ':message' => $recruiterMessage
            ]);

            log_admin_action($db, (int)$authUser['id'], 'update_application_status', [
                'application_id' => $applicationId,
                'status' => $newStatus
            ]);

            $db->commit();

            echo json_encode([
                'success' => true,
                'message' => 'Application status updated'
            ]);
            break;
        }

        case 'send_announcement': {
            $target = (string)($input['target'] ?? '');
            $message = trim((string)($input['message'] ?? ''));
            $userIds = is_array($input['userIds'] ?? null) ? $input['userIds'] : [];

            if ($message === '') {
                auth_json_error(400, 'Message is required');
            }

            $recipientIds = [];
            if ($target === 'all_candidates') {
                $recipientIds = $db->query("SELECT id FROM users WHERE role = 'candidate'")->fetchAll(PDO::FETCH_COLUMN);
            } elseif ($target === 'all_recruiters') {
                $recipientIds = $db->query("SELECT id FROM users WHERE role = 'recruiter'")->fetchAll(PDO::FETCH_COLUMN);
            } elseif ($target === 'all_users') {
                $recipientIds = $db->query("SELECT id FROM users")->fetchAll(PDO::FETCH_COLUMN);
            } elseif ($target === 'specific_users') {
                $recipientIds = array_values(array_filter(array_map('intval', $userIds), static fn($v) => $v > 0));
            } else {
                auth_json_error(400, 'Invalid announcement target');
            }

            if (empty($recipientIds)) {
                auth_json_error(400, 'No recipients found');
            }

            $stmt = $db->prepare("
                INSERT INTO notifications (user_id, application_id, job_id, status, message, is_read, created_at)
                VALUES (:user_id, 0, 0, :status, :message, 0, NOW())
            ");
            foreach ($recipientIds as $uid) {
                $stmt->execute([
                    ':user_id' => (int)$uid,
                    ':status' => 'announcement',
                    ':message' => $message
                ]);
            }

            log_admin_action($db, (int)$authUser['id'], 'send_announcement', [
                'target' => $target,
                'recipient_count' => count($recipientIds)
            ]);

            echo json_encode([
                'success' => true,
                'message' => 'Announcement sent',
                'recipientCount' => count($recipientIds)
            ]);
            break;
        }

        case 'report_candidates': {
            $rows = $db->query("
                SELECT
                    u.id AS candidate_id,
                    u.email,
                    COALESCE(p.first_name, '') AS first_name,
                    COALESCE(p.last_name, '') AS last_name,
                    COALESCE(cp.preferred_location, '') AS preferred_location,
                    COALESCE(cp.experience_years, 0) AS experience_years,
                    COALESCE(app.application_count, 0) AS application_count,
                    COALESCE(res.resume_count, 0) AS resume_count
                FROM users u
                LEFT JOIN profiles p ON p.user_id = u.id
                LEFT JOIN candidate_profiles cp ON cp.user_id = u.id
                LEFT JOIN (
                    SELECT candidate_id, COUNT(*) AS application_count
                    FROM applications
                    GROUP BY candidate_id
                ) app ON app.candidate_id = u.id
                LEFT JOIN (
                    SELECT candidate_id, COUNT(*) AS resume_count
                    FROM candidate_resumes
                    GROUP BY candidate_id
                ) res ON res.candidate_id = u.id
                WHERE u.role = 'candidate'
                ORDER BY u.id DESC
            ")->fetchAll(PDO::FETCH_ASSOC);

            echo json_encode([
                'success' => true,
                'rows' => $rows
            ]);
            break;
        }

        case 'report_applications': {
            $rows = $db->query("
                SELECT
                    a.id AS application_id,
                    a.applied_at,
                    COALESCE(NULLIF(a.status, ''), 'pending') AS status,
                    j.title AS job_title,
                    cu.email AS candidate_email,
                    ru.email AS recruiter_email,
                    COALESCE(NULLIF(TRIM(rp.company_name), ''), ru.email) AS company_name
                FROM applications a
                JOIN jobs j ON j.id = a.job_id
                JOIN users cu ON cu.id = a.candidate_id
                JOIN users ru ON ru.id = j.recruiter_id
                LEFT JOIN recruiter_profiles rp ON rp.user_id = j.recruiter_id
                ORDER BY a.applied_at DESC
            ")->fetchAll(PDO::FETCH_ASSOC);

            echo json_encode([
                'success' => true,
                'rows' => $rows
            ]);
            break;
        }

        case 'list_audit_logs': {
            $limit = max(1, min(500, (int)($input['limit'] ?? 100)));
            $stmt = $db->prepare("
                SELECT
                    l.id,
                    l.admin_user_id,
                    u.email AS admin_email,
                    l.action,
                    l.details,
                    l.created_at
                FROM admin_audit_logs l
                LEFT JOIN users u ON u.id = l.admin_user_id
                ORDER BY l.created_at DESC
                LIMIT :limit
            ");
            $stmt->bindValue(':limit', $limit, PDO::PARAM_INT);
            $stmt->execute();

            echo json_encode([
                'success' => true,
                'logs' => $stmt->fetchAll(PDO::FETCH_ASSOC)
            ]);
            break;
        }

        default:
            auth_json_error(400, 'Unsupported action');
    }
} catch (Exception $e) {
    if (isset($db) && $db->inTransaction()) {
        $db->rollBack();
    }
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'message' => $e->getMessage()
    ]);
}

