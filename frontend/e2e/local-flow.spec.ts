import { expect, test } from '@playwright/test';

test('register, create a group, add a bill, and review it', async ({ page }) => {
  const username = `e2e_${Date.now()}`;
  await page.goto('/');
  await page.getByRole('button', { name: '第一次使用？建立帳戶' }).click();
  await page.getByLabel('帳戶名稱').fill(username);
  await page.getByLabel('你的名字').fill('E2E User');
  await page.getByLabel('電郵（用於聯絡）').fill(`${username}@example.com`);
  await page.getByLabel('密碼').fill('password123');
  await page.getByRole('button', { name: '建立帳戶' }).click();

  await expect(page.getByText('先建立一個群組')).toBeVisible();
  await page.getByRole('button', { name: '建立群組' }).click();
  await page.getByLabel('群組名稱').fill('E2E Group');
  await page.getByRole('button', { name: '建立群組' }).last().click();
  await expect(page.getByRole('heading', { name: 'E2E Group' })).toBeVisible();

  await page.getByRole('button', { name: '＋ 記一筆開支' }).click();
  await page.getByLabel('這次叫什麼？').fill('E2E Lunch');
  await page.getByLabel('金額 HK$').fill('25.50');
  await page.getByLabel('簡單描述').fill('Lunch');
  await page.getByRole('button', { name: '繼續分帳 →' }).click();
  await expect(page.getByText('HK$25.50').first()).toBeVisible();
  await page.getByRole('button', { name: '完成並記錄 ✓' }).click();
  await expect(page.getByText('E2E Lunch')).toBeVisible();
});

test('a second group does not duplicate the owner in a new bill', async ({ page }) => {
  const username = `second_${Date.now()}`;
  await page.goto('/');
  await page.getByRole('button', { name: '第一次使用？建立帳戶' }).click();
  await page.getByLabel('帳戶名稱').fill(username);
  await page.getByLabel('你的名字').fill('Second Group User');
  await page.getByLabel('電郵（用於聯絡）').fill(`${username}@example.com`);
  await page.getByLabel('密碼').fill('password123');
  await page.getByRole('button', { name: '建立帳戶' }).click();
  await page.getByRole('button', { name: '建立群組' }).click();
  await page.getByLabel('群組名稱').fill('First Group');
  await page.getByRole('button', { name: '建立群組' }).last().click();
  await page.getByRole('button', { name: '＋ 新增群組' }).click();
  await page.getByLabel('群組名稱').fill('Second Group');
  await page.getByRole('button', { name: '建立群組' }).last().click();
  await page.getByRole('button', { name: '＋ 記一筆開支' }).click();
  await page.getByLabel('金額 HK$').fill('100.00');
  await page.getByLabel('簡單描述').fill('Second group meal');
  await page.getByRole('button', { name: '繼續分帳 →' }).click();
  await page.getByRole('button', { name: '完成並記錄 ✓' }).click();
  await expect(page.getByText('Second group meal')).toBeVisible();
});

test('a recipient payment card offers image sharing and PNG download', async ({ page }) => {
  const username = `image_${Date.now()}`;
  await page.goto('/');
  await page.getByRole('button', { name: '第一次使用？建立帳戶' }).click();
  await page.getByLabel('帳戶名稱').fill(username);
  await page.getByLabel('你的名字').fill('Image Owner');
  await page.getByLabel('電郵（用於聯絡）').fill(`${username}@example.com`);
  await page.getByLabel('密碼').fill('password123');
  await page.getByRole('button', { name: '建立帳戶' }).click();
  await page.getByRole('button', { name: '建立群組' }).click();
  await page.getByLabel('群組名稱').fill('Image Group');
  await page.getByRole('button', { name: '建立群組' }).last().click();
  await page.getByRole('button', { name: '成員 / 朋友' }).click();
  await page.getByPlaceholder('例如：Alice').fill('Alice');
  await page.getByRole('button', { name: '＋ 加入' }).click();
  await page.getByRole('button', { name: '×' }).click();
  await page.getByRole('button', { name: '＋ 記一筆開支' }).click();
  await page.getByLabel('這次叫什麼？').fill('Image invoice dinner');
  await page.getByLabel('金額 HK$').fill('80.00');
  await page.getByLabel('簡單描述').fill('Image invoice dinner');
  await page.getByRole('button', { name: /Alice/ }).click();
  await page.getByRole('button', { name: '繼續分帳 →' }).click();
  await page.getByRole('button', { name: '完成並記錄 ✓' }).click();
  await page.getByText('Image invoice dinner').click();
  await page.getByRole('button', { name: '建立付款單' }).click();
  await expect(page.getByRole('button', { name: '分享圖片' })).toBeVisible();
  await expect(page.getByRole('button', { name: '下載 PNG' })).toBeVisible();
});
