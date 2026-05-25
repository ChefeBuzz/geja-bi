# ⚙️ Setup — BI GEJA Auto-Update

## Como ativar a atualização automática

### 1. Adicionar Secret GEJA_SA_KEY

1. Acesse: https://github.com/ChefeBuzz/geja-bi/settings/secrets/actions
2. Clique em **New repository secret**
3. Nome: `GEJA_SA_KEY`
4. Valor: cole o conteúdo do arquivo `data-geja-5f503fb3a23f.json`
5. Clique em **Add secret**

### 2. Criar o Workflow

1. Acesse: https://github.com/ChefeBuzz/geja-bi/actions
2. Clique em **set up a workflow yourself**
3. Cole o conteúdo do arquivo `workflow-template.yml`
4. Clique em **Commit changes**

### 3. Rodar manualmente (primeira vez)

1. Acesse: https://github.com/ChefeBuzz/geja-bi/actions
2. Clique em **Atualizar BI GEJA**
3. Clique em **Run workflow**

### Agendamento automático
O BI será atualizado automaticamente todo dia às **02:00 BRT**.

### Link do BI
https://chefebuzz.github.io/geja-bi/
