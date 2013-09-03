{-# LANGUAGE InstanceSigs, DisambiguateRecordFields, GADTSyntax, DisambiguateRecordFields #-}

import System.Process (readProcessWithExitCode)
import GHC.IO.Handle (hPutStr, hGetContents, hSetBinaryMode)
import qualified Text.ParserCombinators.Parsec as TPP
import Data.Map (Map, fromList, toList)
import Text.ParserCombinators.Parsec (parse, ParseError, GenParser, many, eof, noneOf, oneOf, char, skipMany, skipMany1, space, spaces, newline, endBy)
import Data.List (intersperse)

data Stage = SpeakerIndependent | SpeakerAdapted1 | SpeakerAdapted2 deriving (Eq)

instance Ord Stage where
  compare :: Stage -> Stage -> Ordering
  compare SpeakerIndependent _ = LT
  compare SpeakerAdapted2 _ = GT
  compare SpeakerAdapted1 SpeakerAdapted2 = LT
  compare _ _ = GT
  


{-
data Host = Host {hostname :: String,
                  state :: String,
                  np :: Int,
                  ntype :: String,
                  status :: Map String String,
                  momServicePort :: String,
                  momManagerPort :: String
                  } deriving (Show)
-}

data Host = Host {hostname :: String,
                  fields :: Map String String
                  } deriving (Show)

data JobSpec = JobSpec {name :: String,
                        commands :: [String],
                        resources :: Map String String,
                        dependencies :: [Job],
                        path :: String
                       }

instance Show JobSpec where
  show :: JobSpec -> String
  show j = concat $ intersperse "\n" $ ["#PBS -N " ++ name j] ++ ["#PBS -l " ++ x ++ "=" ++ y|(x, y) <- toList $ resources j] ++ ["cd " ++ path j] ++ [x|x <- commands j]

qnodes :: IO (Either ParseError [Host])
qnodes = do
  (exit, stdout, stderr) <- readProcessWithExitCode "qnodes" [] ""  
  return $ parse nodeInfo "" stdout
  
nodeInfo :: GenParser Char st [Host]
nodeInfo = do
  nodes <- many node
  eof
  return nodes
  
node :: GenParser Char st Host
node = do
  hostname <- host
  fields <- many field
  emptyLine
  return $ Host {hostname=hostname, fields=fromList fields}

field :: GenParser Char st (String, String)
field = do
  skipMany1 $ char ' '    
  property <- many (noneOf "\n=")
  oneOf "="
  value <- many (noneOf "\n")
  eol
  return (property, value)

host :: GenParser Char st String
host = do
  ret <- many (noneOf "\n")
  eol
  return ret

emptyLine :: GenParser Char st ()
emptyLine = do
  eol
  return ()

eol = char '\n'

data Job = Job Int | Array Int Int deriving (Show)

submitJob :: JobSpec -> IO (Either String Job)
submitJob j = do
  (exit, stdout, stderr) <- readProcessWithExitCode "qsub" ["-V", "-h"] (show j)
  return $ Left $ stdout



main = do
  let jobSpec = JobSpec "testjob" ["sleep 30", "exit 0"] (fromList [("hosts", "calculon-minor")]) [] "/mnt/asr"
  --jobId <- submitJob jobSpec
  --(Right hosts) <- qnodes
  --print $ map hostname hosts
  print jobSpec
  --print jobId
