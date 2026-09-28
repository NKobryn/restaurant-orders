# Експерименти з тестування (лабораторна робота №6)

Ці тести навмисно НЕ входять до основного набору (`testpaths = ["tests"]`): частина з них слабкі,
нестабільні або падають, щоб показати проблему. Запуск з кореня проєкту:

```bash
pytest experiments/testing/test_exp1_weak.py --cov=buggy_pricing --cov=order_size --cov-branch --cov-report=term-missing
pytest experiments/testing/test_exp1_strong.py
pytest experiments/testing/test_exp3_branch_partial.py --cov=order_size --cov-branch --cov-report=term-missing
pytest experiments/testing/test_exp3_branch_full.py --cov=order_size --cov-branch --cov-report=term-missing
pytest experiments/testing/test_exp4_mock_vs_fake.py -v
for i in $(seq 20); do pytest -q experiments/testing/test_exp5_flaky.py; done
for i in 1 2 3; do pytest -q -s experiments/testing/test_exp6_tmp_path.py; done
```
