CREATE OR REPLACE FUNCTION admin_confirm_user(target_email text)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  UPDATE auth.users
  SET email_confirmed_at = COALESCE(email_confirmed_at, NOW())
  WHERE email = target_email;
  
  RETURN FOUND;
END;
$$;

-- To Test: SELECT admin_confirm_user('user@example.com');


CREATE OR REPLACE FUNCTION admin_confirm_all_pending_users()
RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  updated_count integer;
BEGIN
  UPDATE auth.users
  SET email_confirmed_at = NOW()
  WHERE email_confirmed_at IS NULL;
  
  GET DIAGNOSTICS updated_count = ROW_COUNT;
  RETURN updated_count;
END;
$$;

-- To Test: SELECT admin_confirm_all_pending_users();
