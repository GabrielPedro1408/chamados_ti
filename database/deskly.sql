-- =============================================================
-- Deskly - Sistema de Chamados de TI
-- Script de criação do banco (MySQL 8 / MariaDB 10.4+)
--
-- Pode ser executado mais de uma vez: só cria o que ainda não existe.
--   mysql -u root < database/deskly.sql
--
-- Alterações em relação à primeira versão (ver documentacao/Deskly.md):
--   * empresa.SenhaHash: a empresa faz login por CNPJ + senha.
--   * SenhaHash com 255 caracteres: o hash do werkzeug passa de 100.
--   * Tabela "funcionariotecncio" renomeada para "funcionariotecnico".
--   * funcionariotecnico.IdEquipe aceita NULL (técnico sem equipe).
--   * chamado.IdTecnico, Previsao e TempoGasto aceitam NULL: o chamado
--     nasce sem técnico e sem previsão.
--   * chamado.Status, Solucao e DataHoraFechamento: acompanhamento e
--     métricas (resolvidos no dia, tempo médio).
--   * Nova tabela "comentario" para os comentários do técnico.
-- =============================================================

CREATE DATABASE IF NOT EXISTS `deskly` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE `deskly`;

CREATE TABLE IF NOT EXISTS `empresa` (
  `IdEmpresa`   int(10)      NOT NULL AUTO_INCREMENT,
  `RazaoSocial` varchar(255) NOT NULL,
  `Cnpj`        varchar(14)  NOT NULL COMMENT 'Apenas os 14 dígitos',
  `SenhaHash`   varchar(255) NOT NULL,
  PRIMARY KEY (`IdEmpresa`),
  UNIQUE KEY `Cnpj` (`Cnpj`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `setor` (
  `IdSetor`   int(10)     NOT NULL AUTO_INCREMENT,
  `IdEmpresa` int(10)     NOT NULL,
  `NomeSetor` varchar(50) NOT NULL,
  PRIMARY KEY (`IdSetor`),
  KEY `IdEmpresa` (`IdEmpresa`),
  CONSTRAINT `setor_ibfk_1` FOREIGN KEY (`IdEmpresa`) REFERENCES `empresa` (`IdEmpresa`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `equipetecnica` (
  `IdEquipe`   int(10)     NOT NULL AUTO_INCREMENT,
  `IdEmpresa`  int(10)     NOT NULL,
  `NomeEquipe` varchar(50) NOT NULL,
  PRIMARY KEY (`IdEquipe`),
  KEY `IdEmpresa` (`IdEmpresa`),
  CONSTRAINT `equipetecnica_ibfk_1` FOREIGN KEY (`IdEmpresa`) REFERENCES `empresa` (`IdEmpresa`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `usuario` (
  `IdUsuario`   int(10)      NOT NULL AUTO_INCREMENT,
  `IdEmpresa`   int(10)      NOT NULL,
  `NomeUsuario` varchar(255) NOT NULL COMMENT 'MAIÚSCULO e sem espaços',
  `SenhaHash`   varchar(255) NOT NULL,
  PRIMARY KEY (`IdUsuario`),
  UNIQUE KEY `NomeUsuario` (`NomeUsuario`),
  KEY `IdEmpresa` (`IdEmpresa`),
  CONSTRAINT `usuario_ibfk_1` FOREIGN KEY (`IdEmpresa`) REFERENCES `empresa` (`IdEmpresa`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `funcionariotecnico` (
  `IdTecnico` int(10) NOT NULL AUTO_INCREMENT,
  `IdUsuario` int(10) NOT NULL,
  `IdEquipe`  int(10) DEFAULT NULL,
  PRIMARY KEY (`IdTecnico`),
  UNIQUE KEY `IdUsuario` (`IdUsuario`),
  KEY `IdEquipe` (`IdEquipe`),
  CONSTRAINT `funcionariotecnico_ibfk_1` FOREIGN KEY (`IdUsuario`) REFERENCES `usuario` (`IdUsuario`),
  CONSTRAINT `funcionariotecnico_ibfk_2` FOREIGN KEY (`IdEquipe`) REFERENCES `equipetecnica` (`IdEquipe`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `funcionariopadrao` (
  `IdFuncionario` int(10) NOT NULL AUTO_INCREMENT,
  `IdUsuario`     int(10) NOT NULL,
  `IdSetor`       int(10) NOT NULL,
  PRIMARY KEY (`IdFuncionario`),
  UNIQUE KEY `IdUsuario` (`IdUsuario`),
  KEY `IdSetor` (`IdSetor`),
  CONSTRAINT `funcionariopadrao_ibfk_1` FOREIGN KEY (`IdUsuario`) REFERENCES `usuario` (`IdUsuario`),
  CONSTRAINT `funcionariopadrao_ibfk_2` FOREIGN KEY (`IdSetor`) REFERENCES `setor` (`IdSetor`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `prioridade` (
  `IdPrioridade`        int(10)     NOT NULL AUTO_INCREMENT,
  `DescricaoPrioridade` varchar(30) DEFAULT NULL,
  PRIMARY KEY (`IdPrioridade`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT IGNORE INTO `prioridade` (`IdPrioridade`, `DescricaoPrioridade`) VALUES
(1, 'Crítica'),
(2, 'Alta'),
(3, 'Média'),
(4, 'Baixa');

CREATE TABLE IF NOT EXISTS `chamado` (
  `IdChamado`          int(10)      NOT NULL AUTO_INCREMENT,
  `IdEmpresa`          int(10)      NOT NULL,
  `IdTecnico`          int(10)      DEFAULT NULL COMMENT 'NULL até um técnico assumir',
  `IdFuncionario`      int(10)      NOT NULL,
  `IdPrioridade`       int(10)      NOT NULL,
  `Descricao`          varchar(500) NOT NULL,
  `Previsao`           varchar(25)  DEFAULT NULL,
  `DataHoraAbertura`   datetime     NOT NULL,
  `TempoGasto`         int(11)      DEFAULT NULL COMMENT 'Minutos da abertura até a finalização',
  `Status`             varchar(20)  NOT NULL DEFAULT 'aguardando' COMMENT 'aguardando | em_andamento | finalizado',
  `Solucao`            varchar(1000) DEFAULT NULL,
  `DataHoraFechamento` datetime     DEFAULT NULL,
  PRIMARY KEY (`IdChamado`),
  KEY `IdEmpresa` (`IdEmpresa`),
  KEY `IdTecnico` (`IdTecnico`),
  KEY `IdFuncionario` (`IdFuncionario`),
  KEY `IdPrioridade` (`IdPrioridade`),
  CONSTRAINT `chamado_ibfk_1` FOREIGN KEY (`IdEmpresa`) REFERENCES `empresa` (`IdEmpresa`),
  CONSTRAINT `chamado_ibfk_2` FOREIGN KEY (`IdTecnico`) REFERENCES `funcionariotecnico` (`IdTecnico`),
  CONSTRAINT `chamado_ibfk_3` FOREIGN KEY (`IdFuncionario`) REFERENCES `funcionariopadrao` (`IdFuncionario`),
  CONSTRAINT `chamado_ibfk_4` FOREIGN KEY (`IdPrioridade`) REFERENCES `prioridade` (`IdPrioridade`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS `comentario` (
  `IdComentario` int(10)      NOT NULL AUTO_INCREMENT,
  `IdChamado`    int(10)      NOT NULL,
  `IdUsuario`    int(10)      NOT NULL,
  `Texto`        varchar(500) NOT NULL,
  `DataHora`     datetime     NOT NULL,
  PRIMARY KEY (`IdComentario`),
  KEY `IdChamado` (`IdChamado`),
  KEY `IdUsuario` (`IdUsuario`),
  CONSTRAINT `comentario_ibfk_1` FOREIGN KEY (`IdChamado`) REFERENCES `chamado` (`IdChamado`) ON DELETE CASCADE,
  CONSTRAINT `comentario_ibfk_2` FOREIGN KEY (`IdUsuario`) REFERENCES `usuario` (`IdUsuario`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
